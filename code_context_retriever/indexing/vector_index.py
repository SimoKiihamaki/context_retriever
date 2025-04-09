import os
import logging
import pickle
import time
from typing import List, Dict, Any, Optional, Tuple

import numpy as np

from ..utils.logging import get_logger

logger = get_logger(__name__)

# Try to import FAISS
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    from sklearn.metrics.pairwise import cosine_similarity
    logger.warning("FAISS not available, falling back to sklearn cosine similarity")

class VectorIndex:
    """
    Vector index for storing and searching embeddings.
    Uses FAISS if available, otherwise falls back to numpy-based cosine similarity.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the vector index.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.index_dir = config.get('index_dir', '.cache/vector_index')
        self.use_faiss = FAISS_AVAILABLE and config.get('use_faiss', True)
        self.metric = config.get('metric', 'l2')  # 'l2' or 'cosine'
        
        self.index = None
        self.metadata = []
        self.dimension = None
        
        # Create index directory if it doesn't exist
        if not os.path.exists(self.index_dir):
            os.makedirs(self.index_dir, exist_ok=True)
    
    def build(self, embeddings: np.ndarray, metadata: List[Dict[str, Any]]) -> None:
        """
        Build the vector index from embeddings and metadata.
        
        Args:
            embeddings: 2D array of embeddings
            metadata: List of metadata dictionaries
        """
        if len(embeddings) == 0:
            logger.warning("No embeddings provided to build index")
            return
        
        self.metadata = metadata
        self.dimension = embeddings.shape[1]
        
        # Convert to float32 which is required by FAISS
        embeddings = embeddings.astype(np.float32)
        
        if self.use_faiss:
            if self.metric == 'cosine':
                # L2 normalize for cosine similarity
                faiss.normalize_L2(embeddings)
                self.index = faiss.IndexFlatIP(self.dimension)  # Inner product for cosine similarity
            else:
                self.index = faiss.IndexFlatL2(self.dimension)  # L2 distance
            
            self.index.add(embeddings)
            logger.info(f"Built FAISS index with {len(embeddings)} vectors, dimension {self.dimension}")
        else:
            self.index = embeddings
            logger.info(f"Built numpy index with {len(embeddings)} vectors, dimension {self.dimension}")
    
    def search(self, query_embedding: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Search for the nearest neighbors in the index.
        
        Args:
            query_embedding: Query embedding vector
            top_k: Number of results to return
            
        Returns:
            List of dictionaries with metadata and distance/similarity scores
        """
        if self.index is None:
            logger.error("Index not built yet")
            return []
        
        # Ensure query is in the right shape and type
        query_embedding = np.array(query_embedding).reshape(1, -1).astype(np.float32)
        
        if self.use_faiss:
            if self.metric == 'cosine':
                # L2 normalize for cosine similarity
                faiss.normalize_L2(query_embedding)
                distances, indices = self.index.search(query_embedding, min(top_k, len(self.metadata)))
                
                # Convert distances to similarities (inner product distances are already similarities)
                similarities = distances
            else:
                distances, indices = self.index.search(query_embedding, min(top_k, len(self.metadata)))
                
                # Convert L2 distances to similarities (lower distance = higher similarity)
                max_dist = np.max(distances) + 1e-6  # Avoid division by zero
                similarities = 1 - (distances / max_dist)
            
            results = []
            for i, idx in enumerate(indices[0]):
                if idx < len(self.metadata):
                    result = self.metadata[idx].copy()
                    result["score"] = float(similarities[0][i])
                    result["distance"] = float(distances[0][i])
                    results.append(result)
        else:
            if self.metric == 'cosine':
                # Cosine similarity
                sim = cosine_similarity(query_embedding, self.index)[0]
                
                # Get top-k indices
                top_indices = np.argsort(sim)[-min(top_k, len(self.metadata)):][::-1]
                
                results = []
                for idx in top_indices:
                    result = self.metadata[idx].copy()
                    result["score"] = float(sim[idx])
                    result["distance"] = 1 - float(sim[idx])  # Convert similarity to distance
                    results.append(result)
            else:
                # L2 distance
                diff = self.index - query_embedding
                dist = np.sqrt(np.sum(diff * diff, axis=1))
                
                # Get top-k indices (smallest distances)
                top_indices = np.argsort(dist)[:min(top_k, len(self.metadata))]
                
                results = []
                for idx in top_indices:
                    result = self.metadata[idx].copy()
                    result["score"] = 1 - float(dist[idx]) / (float(np.max(dist)) + 1e-6)  # Normalize to similarity
                    result["distance"] = float(dist[idx])
                    results.append(result)
        
        return results
    
    def save(self, name: str = 'default') -> None:
        """
        Save the index and metadata to disk.
        
        Args:
            name: Name of the index
        """
        index_path = os.path.join(self.index_dir, f"{name}.index")
        metadata_path = os.path.join(self.index_dir, f"{name}.metadata")
        
        try:
            # Save metadata
            with open(metadata_path, 'wb') as f:
                pickle.dump({
                    'metadata': self.metadata,
                    'dimension': self.dimension,
                    'metric': self.metric
                }, f)
            
            # Save index
            if self.use_faiss:
                faiss.write_index(self.index, index_path)
            else:
                with open(index_path, 'wb') as f:
                    np.save(f, self.index)
            
            logger.info(f"Saved index to {index_path} and metadata to {metadata_path}")
        except Exception as e:
            logger.error(f"Error saving index: {e}", exc_info=True)
    
    def load(self, name: str = 'default') -> bool:
        """
        Load the index and metadata from disk.
        
        Args:
            name: Name of the index
            
        Returns:
            True if successfully loaded, False otherwise
        """
        index_path = os.path.join(self.index_dir, f"{name}.index")
        metadata_path = os.path.join(self.index_dir, f"{name}.metadata")
        
        if not os.path.exists(index_path) or not os.path.exists(metadata_path):
            logger.error(f"Index files not found: {index_path} or {metadata_path}")
            return False
        
        try:
            # Load metadata
            with open(metadata_path, 'rb') as f:
                metadata_dict = pickle.load(f)
                self.metadata = metadata_dict['metadata']
                self.dimension = metadata_dict['dimension']
                self.metric = metadata_dict.get('metric', self.metric)
            
            # Load index
            if self.use_faiss:
                self.index = faiss.read_index(index_path)
            else:
                with open(index_path, 'rb') as f:
                    self.index = np.load(f)
            
            logger.info(f"Loaded index from {index_path} and metadata from {metadata_path}")
            return True
        except Exception as e:
            logger.error(f"Error loading index: {e}", exc_info=True)
            return False

