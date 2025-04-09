import re
import logging
import os
from typing import List, Dict, Any, Set, Optional, Tuple

from .base import BaseExtractor

logger = logging.getLogger(__name__)

class TypeScriptExtractor(BaseExtractor):
    """
    Extract code chunks from TypeScript files using regex-based parsing.
    For a production environment, consider replacing this with a proper TypeScript parser.
    """
    
    @classmethod
    def get_supported_extensions(cls) -> Set[str]:
        """Get the set of file extensions supported by this extractor."""
        return {'.ts', '.tsx', '.js', '.jsx'}
    
    def extract_chunks(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract functions, classes, and interfaces from a TypeScript file.
        
        Args:
            file_path: Path to the TypeScript file
            
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
            
            # Extract different types of definitions
            chunks.extend(self._extract_functions(file_path, content))
            chunks.extend(self._extract_classes(file_path, content))
            chunks.extend(self._extract_interfaces(file_path, content))
            chunks.extend(self._extract_arrow_functions(file_path, content))
            
            logger.debug(f"Extracted {len(chunks)} chunks from {file_path}")
            return chunks
            
        except Exception as e:
            logger.error(f"Error extracting chunks from {file_path}: {e}", exc_info=True)
            return chunks
    
    def _extract_functions(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Extract standard function definitions."""
        chunks = []
        # Match: function name(...) {...}
        pattern = re.compile(r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\([^)]*\)\s*(?::\s*[^{]+)?\s*\{', re.MULTILINE)
        
        for match in pattern.finditer(content):
            name = match.group(1)
            start_pos = match.start()
            
            # Find the docstring before the function
            docstring = self._extract_docstring(content, start_pos)
            
            # Find the full function body
            snippet, line_start, line_end = self._extract_code_block(content, start_pos)
            
            if snippet:
                chunks.append({
                    "file": file_path,
                    "name": name,
                    "type": "function",
                    "code": snippet,
                    "docstring": docstring,
                    "full_text": f"{snippet}\n{docstring}" if docstring else snippet,
                    "line_start": line_start,
                    "line_end": line_end
                })
        
        return chunks
    
    def _extract_classes(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Extract class definitions."""
        chunks = []
        # Match: class Name {...}
        pattern = re.compile(r'(?:export\s+)?class\s+(\w+)(?:\s+extends\s+\w+)?(?:\s+implements\s+[^{]+)?\s*\{', re.MULTILINE)
        
        for match in pattern.finditer(content):
            name = match.group(1)
            start_pos = match.start()
            
            # Find the docstring before the class
            docstring = self._extract_docstring(content, start_pos)
            
            # Find the full class body
            snippet, line_start, line_end = self._extract_code_block(content, start_pos)
            
            if snippet:
                chunks.append({
                    "file": file_path,
                    "name": name,
                    "type": "class",
                    "code": snippet,
                    "docstring": docstring,
                    "full_text": f"{snippet}\n{docstring}" if docstring else snippet,
                    "line_start": line_start,
                    "line_end": line_end
                })
        
        return chunks
    
    def _extract_interfaces(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Extract interface definitions."""
        chunks = []
        # Match: interface Name {...}
        pattern = re.compile(r'(?:export\s+)?interface\s+(\w+)(?:\s+extends\s+[^{]+)?\s*\{', re.MULTILINE)
        
        for match in pattern.finditer(content):
            name = match.group(1)
            start_pos = match.start()
            
            # Find the docstring before the interface
            docstring = self._extract_docstring(content, start_pos)
            
            # Find the full interface body
            snippet, line_start, line_end = self._extract_code_block(content, start_pos)
            
            if snippet:
                chunks.append({
                    "file": file_path,
                    "name": name,
                    "type": "interface",
                    "code": snippet,
                    "docstring": docstring,
                    "full_text": f"{snippet}\n{docstring}" if docstring else snippet,
                    "line_start": line_start,
                    "line_end": line_end
                })
        
        return chunks
    
    def _extract_arrow_functions(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Extract arrow function definitions."""
        chunks = []
        # Match: const name = (...) => {...}
        pattern = re.compile(r'(?:export\s+)?const\s+(\w+)\s*=\s*(?:\([^)]*\)|[^=]+)\s*=>\s*(?:\{|\()', re.MULTILINE)
        
        for match in pattern.finditer(content):
            name = match.group(1)
            start_pos = match.start()
            
            # Find the docstring before the arrow function
            docstring = self._extract_docstring(content, start_pos)
            
            # Find the full arrow function body
            snippet, line_start, line_end = self._extract_code_block(content, start_pos)
            
            if snippet:
                chunks.append({
                    "file": file_path,
                    "name": name,
                    "type": "arrow_function",
                    "code": snippet,
                    "docstring": docstring,
                    "full_text": f"{snippet}\n{docstring}" if docstring else snippet,
                    "line_start": line_start,
                    "line_end": line_end
                })
        
        return chunks
    
    def _extract_docstring(self, content: str, pos: int) -> str:
        """Extract JSDoc comment before the code block."""
        search_area = content[:pos].rstrip()
        match = re.search(r'/\*\*(.*?)\*/', search_area, re.DOTALL)
        if match and search_area.endswith(match.group(0)):
            return match.group(1).strip()
        return ""
    
    def _extract_code_block(self, content: str, start_pos: int) -> Tuple[str, int, int]:
        """
        Extract a full code block with balanced braces.
        
        Args:
            content: File content
            start_pos: Starting position in the content
            
        Returns:
            Tuple of (code_snippet, line_start, line_end)
        """
        # Find the opening brace position
        open_brace_pos = content.find('{', start_pos)
        if open_brace_pos == -1:
            return "", 0, 0
        
        # Count opening and closing braces to find the matching closing brace
        brace_count = 1
        pos = open_brace_pos + 1
        
        while pos < len(content) and brace_count > 0:
            if content[pos] == '{':
                brace_count += 1
            elif content[pos] == '}':
                brace_count -= 1
            pos += 1
        
        if brace_count != 0:
            logger.warning(f"Unbalanced braces in TypeScript file at position {start_pos}")
            return "", 0, 0
        
        # Extract the full code block
        end_pos = pos
        snippet = content[start_pos:end_pos]
        
        # Calculate line numbers
        lines_before = content[:start_pos].count('\n') + 1
        lines_after = content[:end_pos].count('\n') + 1
        
        return snippet, lines_before, lines_after