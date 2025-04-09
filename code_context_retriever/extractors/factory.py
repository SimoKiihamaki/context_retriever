import os
import logging
from typing import Dict, Any, List, Type, Optional

from .base import BaseExtractor
from .python_extractor import PythonExtractor
from .typescript_extractor import TypeScriptExtractor
from .markdown_extractor import MarkdownExtractor

logger = logging.getLogger(__name__)

class ExtractorFactory:
    """
    Factory for creating extractors based on file extensions.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the factory.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.extractors = {}
        
        # Register default extractors
        self._register_extractor(PythonExtractor)
        self._register_extractor(TypeScriptExtractor)
        self._register_extractor(MarkdownExtractor)
    
    def _register_extractor(self, extractor_class: Type[BaseExtractor]) -> None:
        """
        Register an extractor class for its supported extensions.
        
        Args:
            extractor_class: Extractor class to register
        """
        for ext in extractor_class.get_supported_extensions():
            self.extractors[ext] = extractor_class
    
    def get_extractor(self, file_path: str) -> Optional[BaseExtractor]:
        """
        Get an extractor for the given file path based on extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Extractor instance or None if no extractor is found
        """
        ext = os.path.splitext(file_path)[1].lower()
        if ext in self.extractors:
            extractor_class = self.extractors[ext]
            # Get extractor-specific config or use default
            extractor_config = self.config.get(extractor_class.__name__, {})
            return extractor_class(extractor_config)
        return None
    
    def extract_chunks(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract chunks from a file using the appropriate extractor.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of dictionaries containing extracted chunks with metadata
        """
        extractor = self.get_extractor(file_path)
        if extractor:
            return extractor.extract_chunks(file_path)
        else:
            logger.warning(f"No extractor found for {file_path}")
            return []