import os
import time
import logging
import fnmatch
from typing import List, Dict, Any, Optional, Tuple
import concurrent.futures

import dspy
from dspy import Module, Signature, InputField, OutputField

from ..config import Config
from ..extractors.factory import ExtractorFactory
from ..embedding.embedder import Embedder
from ..indexing.vector_index import VectorIndex
from ..utils.logging import get_logger

logger = get_logger(__name__)

class CodeContextSignature(Signature):
    """
    DSPy signature for the context retrieval module.
    """
    code_query: str = InputField(desc="Query string (function name, snippet, or natural language query)")
    context: List[str] = OutputField(desc="List of relevant code/documentation snippets")

class EnhancedCodeRetriever(Module):
    """
    DSPy module that retrieves code context from an indexed codebase.
    """
    def __init__(self, vector_index: VectorIndex, embedder: Embedder, config: Dict[str, Any]):
        """
        Initialize the code retriever.
        
        Args:
            vector_index: Vector index for searching
            embedder: Embedder for query embedding
            config: Configuration dictionary
        """
        super().__init__()
        self.vector_index = vector_index
        self.embedder = embedder
        self.config = config
        self.top_k = config.get('top_k', 5)
        self.format_template = config.get('format_template', 
                                        "File: {file} | Type: {type} | Name: {name}\n"
                                        "Score: {score:.4f}\n"
                                        "{separator}\n"
                                        "{full_text}\n"
                                        "{separator}\n")
        self.separator = config.get('separator', '-' * 80)

    def forward(self, code_query: str) -> Dict[str, Any]:
        """
        Retrieve context snippets for a query.
        
        Args:
            code_query: Query string
            
        Returns:
            Dictionary with context snippets
        """
        try:
            # Generate an embedding for the query
            start_time = time.time()
            query_embedding = self.embedder.embed(code_query)
            embed_time = time.time() - start_time
            logger.debug(f"Query embedding took {embed_time:.4f} seconds")
            
            # Retrieve matching chunks from the vector index
            start_time = time.time()
            retrieval_results = self.vector_index.search(query_embedding, top_k=self.top_k)
            search_time = time.time() - start_time
            logger.debug(f"Vector search took {search_time:.4f} seconds")
            
            # Format the retrieved results
            context_snippets = []
            for res in retrieval_results:
                snippet = self.format_template.format(
                    file=res.get('file', 'N/A'),
                    type=res.get('type', 'N/A'),
                    name=res.get('name', 'N/A'),
                    score=res.get('score', 0.0),
                    full_text=res.get('full_text', ''),
                    separator=self.separator
                )
                context_snippets.append(snippet)
            
            logger.info(f"Retrieved {len(context_snippets)} context snippets for query: {code_query[:50]}...")
            return {'context': context_snippets}
        except Exception as e:
            logger.error(f"Error retrieving context: {e}", exc_info=True)
            return {'context': [f"Error: {str(e)}"]}

    def raw_search(self, code_query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Perform a raw search and return the metadata directly.
        
        Args:
            code_query: Query string
            top_k: Number of results to return (overrides the default)
            
        Returns:
            List of metadata dictionaries for the matching chunks
        """
        try:
            # Generate an embedding for the query
            query_embedding = self.embedder.embed(code_query)
            
            # Retrieve matching chunks from the vector index
            k = top_k if top_k is not None else self.top_k
            return self.vector_index.search(query_embedding, top_k=k)
        except Exception as e:
            logger.error(f"Error in raw search: {e}", exc_info=True)
            return []


class CodeContextRetriever:
    """
    Main class for indexing codebase and retrieving context.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the code context retriever.
        
        Args:
            config_path: Path to configuration file
        """
        # Load configuration
        self.config = Config(config_path).config
        
        # Initialize components
        self.extractor_factory = ExtractorFactory(self.config.get('extractors', {}))
        self.embedder = Embedder(self.config.get('embedder', {}))
        self.vector_index = VectorIndex(self.config.get('vector_index', {}))
        
        # Initialize retriever
        self.retriever = None
        
        # Load index if specified
        if self.config.get('auto_load_index', False):
            index_name = self.config.get('index_name', 'default')
            if self.vector_index.load(index_name):
                self.retriever = EnhancedCodeRetriever(
                    self.vector_index, 
                    self.embedder,
                    self.config.get('retriever', {})
                )
    
    def _should_exclude(self, path: str) -> bool:
        """
        Check if a file or directory should be excluded based on configuration.
        
        Args:
            path: Path to check
            
        Returns:
            True if should be excluded, False otherwise
        """
        # Get exclude patterns from config
        indexing_config = self.config.get('indexing', {})
        exclude_dirs = indexing_config.get('exclude_dirs', [])
        exclude_files = indexing_config.get('exclude_files', [])
        
        # Check if path contains any excluded directory
        path_parts = path.split(os.sep)
        for part in path_parts:
            if any(fnmatch.fnmatch(part, pattern) for pattern in exclude_dirs):
                return True
        
        # Check if file matches any excluded pattern
        if os.path.isfile(path):
            base_name = os.path.basename(path)
            if any(fnmatch.fnmatch(base_name, pattern) for pattern in exclude_files):
                return True
        
        return False
    
    def index_codebase(self, root_dir: str, extensions: Optional[List[str]] = None, 
                      parallel: bool = True, save_index: bool = True) -> None:
        """
        Index a codebase by extracting chunks and computing embeddings.
        
        Args:
            root_dir: Root directory of the codebase
            extensions: List of file extensions to process (None for all supported)
            parallel: Whether to use parallel processing
            save_index: Whether to save the index after building
        """
        start_time = time.time()
        all_chunks = []
        
        # Get list of files to process
        files_to_process = []
        for subdir, dirs, files in os.walk(root_dir):
            # Apply directory exclusions
            dirs[:] = [d for d in dirs if not self._should_exclude(os.path.join(subdir, d))]
            
            for fname in files:
                file_path = os.path.join(subdir, fname)
                
                # Check if file should be excluded
                if self._should_exclude(file_path):
                    continue
                
                ext = os.path.splitext(fname)[1].lower()
                
                # Filter by extension if specified
                if extensions and ext not in extensions:
                    continue
                
                # Check if we have an extractor for this file type
                if self.extractor_factory.get_extractor(file_path) is not None:
                    files_to_process.append(file_path)
        
        logger.info(f"Found {len(files_to_process)} files to process")
        
        # Extract chunks from files
        if parallel and len(files_to_process) > 1:
            # Process files in parallel
            max_workers = self.config.get('indexing', {}).get('max_workers', os.cpu_count())
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_file = {
                    executor.submit(self.extractor_factory.extract_chunks, file_path): file_path 
                    for file_path in files_to_process
                }
                
                for future in concurrent.futures.as_completed(future_to_file):
                    file_path = future_to_file[future]
                    try:
                        chunks = future.result()
                        all_chunks.extend(chunks)
                        logger.debug(f"Extracted {len(chunks)} chunks from {file_path}")
                    except Exception as e:
                        logger.error(f"Error processing {file_path}: {e}", exc_info=True)
        else:
            # Process files sequentially
            for file_path in files_to_process:
                try:
                    chunks = self.extractor_factory.extract_chunks(file_path)
                    all_chunks.extend(chunks)
                    logger.debug(f"Extracted {len(chunks)} chunks from {file_path}")
                except Exception as e:
                    logger.error(f"Error processing {file_path}: {e}", exc_info=True)
        
        extraction_time = time.time() - start_time
        logger.info(f"Extracted {len(all_chunks)} chunks in {extraction_time:.2f} seconds")
        
        if not all_chunks:
            logger.warning("No chunks extracted, aborting indexing")
            return
        
        # Compute embeddings
        start_time = time.time()
        texts = [chunk["full_text"] for chunk in all_chunks]
        embeddings = self.embedder.batch_embed(texts)
        embedding_time = time.time() - start_time
        logger.info(f"Computed {len(embeddings)} embeddings in {embedding_time:.2f} seconds")
        
        # Build vector index
        start_time = time.time()
        self.vector_index.build(embeddings, all_chunks)
        indexing_time = time.time() - start_time
        logger.info(f"Built vector index in {indexing_time:.2f} seconds")
        
        # Save index if requested
        if save_index:
            index_name = self.config.get('index_name', 'default')
            self.vector_index.save(index_name)
        
        # Initialize retriever
        self.retriever = EnhancedCodeRetriever(
            self.vector_index, 
            self.embedder,
            self.config.get('retriever', {})
        )
    
    def query(self, query: str, threshold: Optional[float] = None) -> List[str]:
        """
        Query the indexed codebase.
        
        Args:
            query: Query string
            threshold: Minimum similarity score threshold (0.0 to 1.0)
            
        Returns:
            List of relevant context snippets
        """
        if not self.retriever:
            raise ValueError("Retriever not initialized. Index a codebase first or load an existing index.")
        
        # Get raw results for potential filtering
        raw_results = self.raw_query(query)
        
        # Apply threshold filter if specified or use default from config
        if threshold is None:
            threshold = self.config.get('retriever', {}).get('threshold')
        
        filtered_results = []
        if threshold is not None:
            filtered_results = [res for res in raw_results if res.get('score', 0) >= threshold]
        else:
            filtered_results = raw_results
        
        # Format results as strings
        result_strings = []
        for res in filtered_results:
            snippet = self.retriever.format_template.format(
                file=res.get('file', 'N/A'),
                type=res.get('type', 'N/A'),
                name=res.get('name', 'N/A'),
                score=res.get('score', 0.0),
                full_text=res.get('full_text', ''),
                separator=self.retriever.separator
            )
            result_strings.append(snippet)
        
        return result_strings
        
    def raw_query(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Perform a raw query and return the metadata directly.
        
        Args:
            query: Query string
            top_k: Number of results to return (overrides the default)
            
        Returns:
            List of metadata dictionaries for the matching chunks
        """
        if not self.retriever:
            raise ValueError("Retriever not initialized. Index a codebase first or load an existing index.")
        
        return self.retriever.raw_search(query, top_k)