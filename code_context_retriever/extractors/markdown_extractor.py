import re
import logging
import os
from typing import List, Dict, Any, Set

from .base import BaseExtractor

logger = logging.getLogger(__name__)

class MarkdownExtractor(BaseExtractor):
    """
    Extract chunks from Markdown files.
    Splits the content by headings for more granular retrieval.
    """
    
    @classmethod
    def get_supported_extensions(cls) -> Set[str]:
        """Get the set of file extensions supported by this extractor."""
        return {'.md', '.markdown'}
    
    def extract_chunks(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract sections from a Markdown file.
        
        Args:
            file_path: Path to the Markdown file
            
        Returns:
            List of dictionaries containing extracted chunks with metadata
        """
        chunks = []
        
        # Check if the file is valid
        if not self.is_valid_file(file_path):
            return chunks
        
        try:
            # Read the file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # First, add the entire file as a chunk
            chunks.append({
                "file": file_path,
                "name": os.path.basename(file_path),
                "type": "document",
                "code": "",
                "docstring": content,
                "full_text": content,
                "line_start": 1,
                "line_end": content.count('\n') + 1
            })
            
            # Then split by headings for more granular retrieval
            if self.config.get('split_by_headings', True):
                sections = self._split_by_headings(content)
                
                line_count = 1
                for section in sections:
                    heading = section.get('heading', 'Section')
                    content = section.get('content', '')
                    
                    # Skip empty sections
                    if not content.strip():
                        continue
                    
                    # Calculate line numbers
                    section_lines = content.count('\n') + 1
                    line_start = line_count
                    line_end = line_count + section_lines - 1
                    line_count = line_end + 1
                    
                    chunks.append({
                        "file": file_path,
                        "name": f"{os.path.basename(file_path)}:{heading}",
                        "type": "section",
                        "code": "",
                        "docstring": content,
                        "full_text": content,
                        "line_start": line_start,
                        "line_end": line_end
                    })
            
            logger.debug(f"Extracted {len(chunks)} chunks from {file_path}")
            return chunks
            
        except Exception as e:
            logger.error(f"Error extracting chunks from {file_path}: {e}", exc_info=True)
            return chunks
    
    def _split_by_headings(self, content: str) -> List[Dict[str, Any]]:
        """
        Split Markdown content by headings.
        
        Args:
            content: Markdown content
            
        Returns:
            List of dictionaries with 'heading' and 'content' keys
        """
        # Find all headings in the document
        heading_pattern = re.compile(r'^(#{1,6})\s+(.+?)$', re.MULTILINE)
        headings = list(heading_pattern.finditer(content))
        
        sections = []
        
        # If no headings, return the entire content as one section
        if not headings:
            sections.append({
                'heading': 'Document',
                'content': content
            })
            return sections
        
        # Process each heading and its content
        for i, match in enumerate(headings):
            heading = match.group(2).strip()
            heading_pos = match.start()
            
            # Determine the end position (next heading or end of file)
            if i < len(headings) - 1:
                end_pos = headings[i+1].start()
            else:
                end_pos = len(content)
            
            # Extract the section content
            section_content = content[heading_pos:end_pos]
            
            sections.append({
                'heading': heading,
                'content': section_content
            })
        
        return sections