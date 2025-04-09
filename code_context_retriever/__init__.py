"""
Smart Code Context Retriever

A production-ready tool for retrieving context from large codebases 
using DSPy and embeddings. This tool helps AI agents, developers, 
and documentation systems understand and navigate complex repositories
by providing relevant code snippets based on natural language queries.
"""

__version__ = '1.0.0'

from .config import Config
from .retrieval.retriever import CodeContextRetriever, EnhancedCodeRetriever
from .projects import ProjectManager, project_manager

__all__ = ['Config', 'CodeContextRetriever', 'EnhancedCodeRetriever', 'ProjectManager', 'project_manager']