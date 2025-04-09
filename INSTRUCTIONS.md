# AI Agent Integration Guide

## Core Principles
- Uses local `sentence-transformers` by default (no API keys)
- Can switch to API models via config when needed
- Maintains code context cache for performance

## CLI Instructions for AI Agents

## Core Workflow
1. Set the active project
2. Index the codebase  
3. Query for relevant code

## Essential Commands

### 1. Project Setup
```bash
# List all projects
code-context-retriever project list

# View the current project
code-context-retriever project current

# Set active project (if not existing)
code-context-retriever project set PROJECT_NAME /path/to/codebase

# Switch to a different project (if it exists)
code-context-retriever project set another-project
```

### 2. Indexing
```bash 
# Full index (run when codebase changes)
code-context-retriever index

# Partial index (faster updates)
code-context-retriever index src/specific/module
```

### 3. Querying
```bash
# Basic query (returns top 5 matches)
code-context-retriever query "How is authentication implemented?"

# With custom result count
code-context-retriever query "Error handling" --top-k 3

# Project-specific query  
code-context-retriever query "Database schema" --project OTHER_PROJECT
```

## Quick Integration

1. **Initialization**:
```python
from code_context_retriever import CodeContextRetriever
retriever = CodeContextRetriever()  # Uses local model
```

2. **Basic Usage**:
```python
# Get relevant code snippets
contexts = retriever.query("How is error handling implemented?")

# Use in your agent's reasoning
for ctx in contexts[:3]:  # Top 3 results
    print(f"Relevant code ({ctx.score:.2f}): {ctx.text[:100]}...")
```

## Advanced Features

### Custom Configuration
```yaml
# config.yaml
embedder:
  model: "sentence-transformers/all-MiniLM-L6-v2"  # or API model
  cache_dir: ".cache/agent_embeddings"
```

### Batch Processing
```python
# Process multiple queries efficiently
queries = ["auth system", "error handling", "data models"]
results = [retriever.query(q) for q in queries]
```

## Best Practices
- Cache results when possible (enabled by default)
- Use specific queries ("How does X work?" vs "Explain X")
- Combine with other tools for full context understanding
- Always set project first
- Re-index after major code changes
- Use specific natural language queries
- Combine with `jq` for JSON output processing
