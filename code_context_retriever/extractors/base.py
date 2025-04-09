from abc import ABC, abstractmethod
from typing import List, Dict, Any, Set
import os
import logging

logger = logging.getLogger(__name__)

class BaseExtractor(ABC):
    """
    Base class for file content extractors.
    
    All extractors should inherit from this class and implement
    the extract_chunks method.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the extractor.
        
        Args:
            config: Configuration dictionary for the extractor
        """
        self.config = config
        self.max_file_size = config.get('max_file_size', 1024 * 1024)  # Default: 1MB
    
    @abstractmethod
    def extract_chunks(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract chunks from the given file.
        
        Args:
            file_path: Path to the file to extract chunks from
            
        Returns:
            A list of dictionaries containing extracted chunks with metadata
        """
        pass
    
    def is_valid_file(self, file_path: str) -> bool:
        """
        Check if a file is valid for processing.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if the file is valid, False otherwise
        """
        # Check if the file exists
        if not os.path.exists(file_path):
            logger.warning(f"File does not exist: {file_path}")
            return False
        
        # Check if it's a regular file
        if not os.path.isfile(file_path):
            logger.warning(f"Not a regular file: {file_path}")
            return False
        
        # Check file size
        if os.path.getsize(file_path) > self.max_file_size:
            logger.warning(f"File too large: {file_path}")
            return False
        
        # Check if we can read the file
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                f.read(1)
            return True
        except Exception as e:
            logger.warning(f"Cannot read file {file_path}: {e}")
            return False
    
    @staticmethod
    def sanitize_path(file_path: str) -> str:
        """
        Sanitize the file path to prevent directory traversal attacks.
        
        Args:
            file_path: Path to sanitize
            
        Returns:
            Sanitized path
        """
        return os.path.normpath(file_path)
    
    @classmethod
    def get_supported_extensions(cls) -> Set[str]:
        """
        Get the set of file extensions supported by this extractor.
        
        Returns:
            A set of file extensions (e.g., {'.py', '.pyi'})
        """
        return set()

