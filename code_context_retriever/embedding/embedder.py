import os
import json
import logging
import hashlib
from typing import List, Dict, Any, Optional
import concurrent.futures
import time

import numpy as np
from dspy.clients.embedding import Embedder as DSPyEmbedder

# Add this import for local embeddings
try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

from ..utils.logging import get_logger

logger = get_logger(__name__)

class Embedder:
    """
    Wrapper for embeddings with caching capabilities.
    Supports both DSPy embedders and local sentence-transformers models.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the embedder.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.model_name = config.get('model', 'sentence-transformers/all-MiniLM-L6-v2')
        self.cache_dir = config.get('cache_dir', '.cache/embeddings')
        self.use_cache = config.get('use_cache', True)
        self.batch_size = config.get('batch_size', 32)
        self.max_workers = config.get('max_workers', 4)
        
        # Initialize based on model type
        if self.model_name.startswith('sentence-transformers/'):
            if not SENTENCE_TRANSFORMERS_AVAILABLE:
                raise ImportError("sentence-transformers package is required for local models")
                
            st_model_name = self.model_name.replace('sentence-transformers/', '')
            try:
                self.local_model = SentenceTransformer(st_model_name)
                self.embed_dim = self.local_model.get_sentence_embedding_dimension()
                logger.info(f"Using local Sentence Transformers model: {st_model_name}")
                self.embedder = None  # Ensure DSPy is not used
            except Exception as e:
                logger.error(f"Failed to initialize local model: {e}")
                raise
        else:
            # Only initialize DSPy for non-local models
            try:
                self.local_model = None
                self.embedder = DSPyEmbedder(model=self.model_name)
                test_embedding = self.embedder("test")
                self.embed_dim = len(test_embedding)
                logger.info(f"Using DSPy embedder with model: {self.model_name}")
            except Exception as e:
                logger.error(f"Failed to initialize DSPy embedder: {e}")
                raise
        
        # Create cache directory if needed
        if self.use_cache and not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir, exist_ok=True)
    
    def embed(self, text: str) -> np.ndarray:
        """
        Embed a single text string.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as numpy array
        """
        # Check cache first if enabled
        if self.use_cache:
            cached_embedding = self._get_from_cache(text)
            if cached_embedding is not None:
                return cached_embedding
        
        # Generate embedding
        try:
            if self.local_model is not None:
                # Use local Sentence Transformers model
                embedding = self.local_model.encode(text, show_progress_bar=False)
                embedding_np = np.array(embedding)
            else:
                # Use DSPy embedder
                embedding = self.embedder(text)  # DSPy embedder uses __call__
                embedding_np = np.array(embedding)
            
            # Save to cache if enabled
            if self.use_cache:
                self._save_to_cache(text, embedding_np)
            
            return embedding_np
        except Exception as e:
            logger.error(f"Error generating embedding: {e}", exc_info=True)
            # Return zero vector in case of error
            return np.zeros(self.embed_dim)
    
    def batch_embed(self, texts: List[str], batch_size: Optional[int] = None) -> np.ndarray:
        """
        Embed multiple text strings in batches.
        
        Args:
            texts: List of text strings to embed
            batch_size: Number of texts to embed in each batch (default: self.batch_size)
            
        Returns:
            2D array of embedding vectors
        """
        if not texts:
            return np.array([])
        
        batch_size = batch_size or self.batch_size
        batches = [texts[i:i + batch_size] for i in range(0, len(texts), batch_size)]
        batch_results = [None] * len(batches)
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all batches for processing
            futures = []
            for batch_idx, batch in enumerate(batches):
                futures.append(executor.submit(self._process_batch, batch))
            
            # Wait for all futures to complete
            for future in concurrent.futures.as_completed(futures):
                batch_idx = futures.index(future)
                try:
                    batch_results[batch_idx] = future.result()
                except Exception as e:
                    logger.error(f"Error processing batch {batch_idx}: {e}", exc_info=True)
                    # Create zero vectors for failed batch
                    batch_size = len(batches[batch_idx])
                    batch_results[batch_idx] = np.zeros((batch_size, self.embed_dim))
        
        # Combine all batch results
        return np.vstack(batch_results)
    
    def _process_batch(self, texts: List[str]) -> np.ndarray:
        """
        Process a single batch of texts.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            2D array of embedding vectors for the batch
        """
        batch_size = len(texts)
        result = np.zeros((batch_size, self.embed_dim))
        
        # Check cache first if enabled
        if self.use_cache:
            to_embed = []
            cached_embeddings = {}
            
            for i, text in enumerate(texts):
                cached = self._get_from_cache(text)
                if cached is not None:
                    result[i] = cached
                    cached_embeddings[i] = True
                else:
                    to_embed.append((i, text))
        else:
            to_embed = [(i, text) for i, text in enumerate(texts)]
        
        # Generate embeddings for remaining texts
        if to_embed:
            try:
                batch_texts = [text for _, text in to_embed]
                batch_indices = [idx for idx, _ in to_embed]
                
                if self.local_model is not None:
                    # Use local Sentence Transformers model
                    batch_embeddings = self.local_model.encode(batch_texts, show_progress_bar=False)
                else:
                    # Use DSPy embedder - process sequentially since it doesn't support batching
                    batch_embeddings = [self.embedder(text) for text in batch_texts]
                
                # Add embeddings to result
                for j, idx in enumerate(batch_indices):
                    embedding = np.array(batch_embeddings[j])
                    result[idx] = embedding
                    
                    # Save to cache if enabled
                    if self.use_cache:
                        self._save_to_cache(batch_texts[j], embedding)
            except Exception as e:
                logger.error(f"Error generating batch embeddings: {e}", exc_info=True)
                # Let the zero values remain for failed embeddings
        
        return result
    
    def _get_cache_path(self, text: str) -> str:
        """
        Get the cache file path for a text.
        
        Args:
            text: Input text
            
        Returns:
            Path to the cache file
        """
        # Create a hash of the text to use as the filename
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        return os.path.join(self.cache_dir, f"{text_hash}.npy")
    
    def _get_from_cache(self, text: str) -> Optional[np.ndarray]:
        """
        Retrieve embedding from cache if available.
        
        Args:
            text: Input text
            
        Returns:
            Cached embedding or None if not found
        """
        cache_path = self._get_cache_path(text)
        if os.path.exists(cache_path):
            try:
                return np.load(cache_path)
            except Exception as e:
                logger.warning(f"Failed to load cache from {cache_path}: {e}")
                return None
        return None
    
    def _save_to_cache(self, text: str, embedding: np.ndarray) -> None:
        """
        Save embedding to cache.
        
        Args:
            text: Input text
            embedding: Embedding vector
        """
        cache_path = self._get_cache_path(text)
        try:
            np.save(cache_path, embedding)
        except Exception as e:
            logger.warning(f"Failed to save cache to {cache_path}: {e}")
