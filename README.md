# Smart Code Context Retriever

A production-ready tool for retrieving context from large codebases using **local sentence-transformers models** or DSPy embeddings. This tool helps AI agents, developers, and documentation systems understand and navigate complex repositories by providing relevant code snippets based on natural language queries.

## Features

- **Local Model Support**: Uses sentence-transformers by default (no API keys required)
- **Multi-language Support**: Analyzes Python, TypeScript/JavaScript, and Markdown files
- **Smart Extraction**: Extracts functions, classes, interfaces, and documentation with context
- **Semantic Search**: Uses embeddings to find relevant code snippets based on semantic meaning
- **API Support**: Offers both command-line interface and REST API
- **Production-Ready**: Includes logging, error handling, configuration, and performance optimizations
- **Scalable**: Designed to handle large codebases with millions of lines of code

## Installation

First install the core requirements:
```bash
pip install sentence-transformers  # Required for local models
pip install -e .
```

For API-based models (optional):
```bash
pip install dspy-ai
```

Additional features:
```bash
pip install -e ".[faiss]"  # For faster similarity search
pip install -e ".[api]"    # For API server
pip install -e ".[dev]"    # For development tools
pip install -e ".[faiss,api,dev]"  # Full installation with all features
```

## Quick Start

### Project Management

```bash
# Set up a project (this saves the project settings for future use)
code-context-retriever project set my-project /path/to/your/codebase

# View the current project
code-context-retriever project current

# List all projects
code-context-retriever project list

# Switch to a different project
code-context-retriever project set another-project
```

### Index a Codebase

```bash
# Index the current project
code-context-retriever index

# Or specify a directory (without affecting the current project)
code-context-retriever index /path/to/your/codebase
```

### Query the Indexed Codebase

```bash
# Query the current project
code-context-retriever query "How is authentication implemented?"

# Or specify a different project
code-context-retriever query "How is authentication implemented?" --project another-project
```

### Start the API Server

```bash
# Start the API server for the current project
code-context-retriever api --port 8000
```

## Configuration

The tool uses a YAML configuration file that can be customized:

**Recommended local model** (default):
```yaml
# custom_config.yaml
embedder:
  model: "sentence-transformers/all-MiniLM-L6-v2"  # Local model
  cache_dir: ".cache/embeddings"
  use_cache: true
```

**API-based alternative**:
```yaml
# custom_config.yaml
embedder:
  model: "openai/text-embedding-3-small"  # Requires DSPy and API key
retriever:
  top_k: 10
```

Then use it:

```bash
code-context-retriever index /path/to/codebase --config custom_config.yaml
```

## Python API

The Python API supports both local and API-based models:

```python
from code_context_retriever.retrieval.retriever import CodeContextRetriever

# Initialize with default local model
retriever = CodeContextRetriever()  

# Or specify config for API model
# retriever = CodeContextRetriever('path/to/api_config.yaml')

# Index a codebase
retriever.index_codebase('/path/to/your/codebase')

# Query using local embeddings
results = retriever.query("How does authentication work?")
for result in results:
    print(f"Score: {result.score:.4f}")
    print(result.text)
```

## REST API

The API endpoints work with both model types:

### Local Model Example
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Show me error handling examples"}'
```

### API Model Example (requires DSPy config)
```bash
curl -X POST http://localhost:8000/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Explain the login flow", "model": "openai/text-embedding-3-small"}'
```

## Integration with DSPy

This tool integrates seamlessly with other DSPy components:

```python
import dspy
from code_context_retriever.retrieval.retriever import CodeContextRetriever

# Create a DSPy module that uses the code retriever
class CodeAssistant(dspy.Module):
    def __init__(self, retriever):
        super().__init__()
        self.retriever = retriever
        self.generate = dspy.ChainOfThought("question -> answer")
    
    def forward(self, question):
        # Get relevant code context
        context = self.retriever.query(question)
        
        # Generate an answer based on the context
        answer = self.generate(question=question, context="\n\n".join(context))
        return answer

# Initialize and use
retriever = CodeContextRetriever()
retriever.index_codebase('/path/to/codebase')
assistant = CodeAssistant(retriever)

answer = assistant("Explain how the login system works")
print(answer.answer)
```

## Advanced Usage

### Project Management

The tool includes project management features that make it easy to work with multiple codebases:

```bash
# Create and select a project
code-context-retriever project set my-project /path/to/codebase

# Create a project with a custom configuration
code-context-retriever project set my-project /path/to/codebase --config /path/to/custom_config.yaml

# Switch between projects
code-context-retriever project set another-project

# List all projects
code-context-retriever project list

# View current project details
code-context-retriever project current

# Remove a project
code-context-retriever project remove old-project
```

Each project maintains its own settings, including the indexed codebase directory, configuration, and index name. Once a project is set as current, all commands will use that project's context by default.

### Custom File Types

You can extend the tool to support custom file types by implementing new extractors:

```python
from code_context_retriever.extractors.base import BaseExtractor

class CustomExtractor(BaseExtractor):
    @classmethod
    def get_supported_extensions(cls):
        return {'.custom'}
    
    def extract_chunks(self, file_path):
        # Implementation here
        ...
```

### Incremental Indexing

For large codebases that change frequently, you can implement incremental indexing:

```bash
# Index only specific file types
code-context-retriever index --extensions .py .ts

# Re-index just a specific directory
code-context-retriever index /path/to/codebase/src/updated_module
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.