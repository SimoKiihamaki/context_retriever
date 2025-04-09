import ast
import logging
import os
from typing import List, Dict, Any, Set, Optional

from .base import BaseExtractor

logger = logging.getLogger(__name__)

class PythonExtractor(BaseExtractor):
    """
    Extract code chunks from Python files using the AST module.
    """
    
    @classmethod
    def get_supported_extensions(cls) -> Set[str]:
        """Get the set of file extensions supported by this extractor."""
        return {'.py', '.pyi'}
    
    def extract_chunks(self, file_path: str) -> List[Dict[str, Any]]:
        """
        Extract functions, classes, and methods from a Python file.
        
        Args:
            file_path: Path to the Python file
            
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
                file_content = f.read()
            
            # Parse the AST
            module_ast = ast.parse(file_content, filename=file_path)
            
            # Extract module-level docstring
            module_docstring = ast.get_docstring(module_ast)
            if module_docstring:
                chunks.append({
                    "file": file_path,
                    "name": f"{file_path}:module",
                    "type": "module",
                    "code": "",
                    "docstring": module_docstring,
                    "full_text": module_docstring,
                    "line_start": 1,
                    "line_end": len(module_docstring.split('\n')) + 1
                })
            
            # Extract functions and classes
            for node in ast.walk(module_ast):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    chunk = self._extract_node(node, file_path, file_content)
                    if chunk:
                        chunks.append(chunk)
            
            logger.debug(f"Extracted {len(chunks)} chunks from {file_path}")
            return chunks
            
        except Exception as e:
            logger.error(f"Error extracting chunks from {file_path}: {e}", exc_info=True)
            return chunks
    
    def _extract_node(self, node: ast.AST, file_path: str, file_content: str) -> Optional[Dict[str, Any]]:
        """
        Extract information from an AST node.
        
        Args:
            node: AST node (function or class)
            file_path: Path to the file
            file_content: Content of the file
            
        Returns:
            Dictionary containing the extracted information, or None if extraction failed
        """
        try:
            name = node.name
            node_type = type(node).__name__.replace('Def', '').lower()
            
            # Get docstring
            docstring = ast.get_docstring(node) or ""
            
            # Get source code lines
            start_line = node.lineno - 1
            end_line = getattr(node, 'end_lineno', node.lineno)
            if hasattr(node, 'body') and node.body:
                end_body = max(getattr(n, 'end_lineno', node.lineno) for n in node.body)
                end_line = max(end_line, end_body)
            
            code_lines = file_content.splitlines()[start_line:end_line]
            code_snippet = "\n".join(code_lines)
            
            # Combine code and docstring for full text
            full_text = f"{code_snippet}\n{docstring}" if docstring else code_snippet
            
            return {
                "file": file_path,
                "name": name,
                "type": node_type,
                "code": code_snippet,
                "docstring": docstring,
                "full_text": full_text,
                "line_start": start_line + 1,
                "line_end": end_line
            }
        except Exception as e:
            logger.error(f"Error extracting node {getattr(node, 'name', 'unknown')}: {e}")
            return None

