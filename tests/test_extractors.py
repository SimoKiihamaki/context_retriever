import os
import tempfile
import pytest

from code_context_retriever.extractors.python_extractor import PythonExtractor
from code_context_retriever.extractors.typescript_extractor import TypeScriptExtractor
from code_context_retriever.extractors.markdown_extractor import MarkdownExtractor

class TestPythonExtractor:
    def test_extract_function(self):
        # Create a temporary Python file
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as f:
            f.write(b'''
def test_function():
    """This is a test docstring."""
    return True
''')
            temp_file = f.name
        
        try:
            # Extract chunks
            extractor = PythonExtractor({})
            chunks = extractor.extract_chunks(temp_file)
            
            # Verify results
            assert len(chunks) == 1
            assert chunks[0]['name'] == 'test_function'
            assert chunks[0]['type'] == 'function'
            assert "This is a test docstring" in chunks[0]['docstring']
        finally:
            # Clean up
            os.unlink(temp_file)
    
    def test_extract_class(self):
        # Create a temporary Python file
        with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as f:
            f.write(b'''
class TestClass:
    """This is a class docstring."""
    def method(self):
        """This is a method docstring."""
        return True
''')
            temp_file = f.name
        
        try:
            # Extract chunks
            extractor = PythonExtractor({})
            chunks = extractor.extract_chunks(temp_file)
            
            # Verify results
            assert len(chunks) == 2
            class_chunk = next((c for c in chunks if c['name'] == 'TestClass'), None)
            method_chunk = next((c for c in chunks if c['name'] == 'method'), None)
            
            assert class_chunk is not None
            assert class_chunk['type'] == 'class'
            assert "This is a class docstring" in class_chunk['docstring']
            
            assert method_chunk is not None
            assert method_chunk['type'] == 'function'
            assert "This is a method docstring" in method_chunk['docstring']
        finally:
            # Clean up
            os.unlink(temp_file)

class TestTypeScriptExtractor:
    def test_extract_function(self):
        # Create a temporary TypeScript file
        with tempfile.NamedTemporaryFile(suffix='.ts', delete=False) as f:
            f.write(b'''
/**
 * This is a test function.
 */
function testFunction() {
    return true;
}
''')
            temp_file = f.name
        
        try:
            # Extract chunks
            extractor = TypeScriptExtractor({})
            chunks = extractor.extract_chunks(temp_file)
            
            # Verify results
            assert len(chunks) == 1
            assert chunks[0]['name'] == 'testFunction'
            assert chunks[0]['type'] == 'function'
            assert "This is a test function" in chunks[0]['docstring']
        finally:
            # Clean up
            os.unlink(temp_file)
    
    def test_extract_arrow_function(self):
        # Create a temporary TypeScript file
        with tempfile.NamedTemporaryFile(suffix='.ts', delete=False) as f:
            f.write(b'''
/**
 * This is a test arrow function.
 */
const arrowFunc = () => {
    return true;
};
''')
            temp_file = f.name
        
        try:
            # Extract chunks
            extractor = TypeScriptExtractor({})
            chunks = extractor.extract_chunks(temp_file)
            
            # Verify results
            assert len(chunks) == 1
            assert chunks[0]['name'] == 'arrowFunc'
            assert chunks[0]['type'] == 'arrow_function'
            assert "This is a test arrow function" in chunks[0]['docstring']
        finally:
            # Clean up
            os.unlink(temp_file)

class TestMarkdownExtractor:
    def test_extract_markdown(self):
        # Create a temporary Markdown file
        with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as f:
            f.write(b'''
# Title

This is a test markdown file.

## Section 1

Content of section 1.

## Section 2

Content of section 2.
''')
            temp_file = f.name
        
        try:
            # Extract chunks
            extractor = MarkdownExtractor({'split_by_headings': True})
            chunks = extractor.extract_chunks(temp_file)
            
            # Verify results
            assert len(chunks) > 1
            
            # Check for whole document
            doc_chunk = next((c for c in chunks if c['type'] == 'document'), None)
            assert doc_chunk is not None
            assert "This is a test markdown file" in doc_chunk['full_text']
            
            # Check for sections
            section1 = next((c for c in chunks if "Section 1" in c['name']), None)
            section2 = next((c for c in chunks if "Section 2" in c['name']), None)
            
            assert section1 is not None
            assert "Content of section 1" in section1['full_text']
            
            assert section2 is not None
            assert "Content of section 2" in section2['full_text']
        finally:
            # Clean up
            os.unlink(temp_file)