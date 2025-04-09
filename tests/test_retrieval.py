import os
import tempfile
import numpy as np
import pytest
from unittest.mock import patch, MagicMock

from code_context_retriever.retrieval.retriever import CodeContextRetriever, EnhancedCodeRetriever
from code_context_retriever.indexing.vector_index import VectorIndex
from code_context_retriever.embedding.embedder import Embedder

class TestEnhancedCodeRetriever:
    @pytest.fixture
    def mock_setup(self):
        # Mock vector index
        mock_vector_index = MagicMock(spec=VectorIndex)
        mock_vector_index.search.return_value = [
            {
                'file': 'test_file.py',
                'name': 'test_function',
                'type': 'function',
                'full_text': 'def test_function():\n    """Test function."""\n    return True',
                'score': 0.95
            },
            {
                'file': 'test_file2.py',
                'name': 'another_function',
                'type': 'function',
                'full_text': 'def another_function():\n    """Another test."""\n    return False',
                'score': 0.85
            }
        ]
        
        # Mock embedder
        mock_embedder = MagicMock(spec=Embedder)
        mock_embedder.embed.return_value = np.random.rand(384)
        
        # Config
        config = {
            'top_k': 2,
            'format_template': "File: {file} | Type: {type} | Name: {name}\nScore: {score:.4f}\n{full_text}",
            'separator': '-' * 80
        }
        
        return mock_vector_index, mock_embedder, config
    
    def test_forward(self, mock_setup):
        mock_vector_index, mock_embedder, config = mock_setup
        
        # Create retriever
        retriever = EnhancedCodeRetriever(mock_vector_index, mock_embedder, config)
        
        # Test query
        result = retriever(code_query="test query")
        
        # Verify results
        assert mock_embedder.embed.called
        assert mock_vector_index.search.called
        assert len(result.context) == 2
        assert "test_function" in result.context[0]
        assert "another_function" in result.context[1]
    
    def test_raw_search(self, mock_setup):
        mock_vector_index, mock_embedder, config = mock_setup
        
        # Create retriever
        retriever = EnhancedCodeRetriever(mock_vector_index, mock_embedder, config)
        
        # Test raw search
        results = retriever.raw_search("test query", top_k=3)
        
        # Verify results
        assert mock_embedder.embed.called
        assert mock_vector_index.search.called
        assert len(results) == 2  # Based on the mock setup
        assert results[0]['name'] == 'test_function'
        assert results[1]['name'] == 'another_function'

class TestCodeContextRetriever:
    @pytest.fixture
    def temp_config(self):
        with tempfile.NamedTemporaryFile(suffix='.yaml', delete=False) as f:
            f.write(b'''
auto_load_index: false
index_name: test_index
embedder:
  model: test_model
  use_cache: false
vector_index:
  use_faiss: false
retriever:
  top_k: 3
indexing:
  exclude_dirs: [".git", "venv"]
  exclude_files: ["*.pyc"]
''')
            temp_file = f.name
        
        try:
            yield temp_file
        finally:
            os.unlink(temp_file)
    
    @patch('code_context_retriever.embedding.embedder.Embedder')
    @patch('code_context_retriever.indexing.vector_index.VectorIndex')
    @patch('code_context_retriever.extractors.factory.ExtractorFactory')
    def test_initialization(self, mock_factory, mock_vector_index, mock_embedder, temp_config):
        # Create retriever
        retriever = CodeContextRetriever(temp_config)
        
        # Verify initialization
        assert mock_factory.called
        assert mock_vector_index.called
        assert mock_embedder.called
        assert retriever.config['index_name'] == 'test_index'
        assert retriever.config['retriever']['top_k'] == 3
    
    def test_should_exclude(self, temp_config):
        # Create retriever
        retriever = CodeContextRetriever(temp_config)
        
        # Test exclusions
        assert retriever._should_exclude('.git/config')
        assert retriever._should_exclude('venv/lib/python3.8')
        assert retriever._should_exclude('src/module/__pycache__')
        assert retriever._should_exclude('src/module/test.pyc')
        
        # Test non-exclusions
        assert not retriever._should_exclude('src/module/test.py')
        assert not retriever._should_exclude('docs/README.md')