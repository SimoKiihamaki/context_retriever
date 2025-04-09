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
# Basic query (saves results to context.txt)
code-context-retriever query "How is authentication implemented?"

# With custom result count
code-context-retriever query "Error handling" --top-k 3

# With similarity score threshold
code-context-retriever query "auth system" --threshold 0.7

# Specify custom output file
code-context-retriever query "login flow" --output login_results.txt

# Display results in terminal (in addition to saving to file)
code-context-retriever query "user validation" --terminal

# Combining options
code-context-retriever query "login flow" --threshold 0.6 --top-k 10 --output login_results.txt

# Project-specific query  
code-context-retriever query "Database schema" --project OTHER_PROJECT
```

By default, all query results are saved to a file named `context.txt` in the current directory, overwriting any existing content. Only a summary is printed to the terminal unless the `--terminal` flag is used.

## Quick Integration

1. **Initialization**:
```python
from code_context_retriever import CodeContextRetriever
retriever = CodeContextRetriever()  # Uses local model
```

2. **Basic Usage**:
```python
# Get relevant code snippets (uses default threshold of 0.35)
contexts = retriever.query("How is error handling implemented?")

# Custom threshold for higher precision
contexts = retriever.query("authentication system", threshold=0.7)

# Save results to a file programmatically
with open("context.txt", "w") as f:
    for i, ctx in enumerate(contexts, 1):
        f.write(f"Result {i}:\n{ctx}\n\n")

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
retriever:
  top_k: 10
  threshold: 0.5  # Minimum similarity score (0.0 to 1.0)
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
- Adjust similarity threshold based on needs:
  - Higher threshold (0.7+) for high-precision results
  - Lower threshold (0.3-0.5) for broader coverage
  - Default (0.35) is a good balance for most use cases
- Set threshold to 0 to disable filtering entirely
- Review saved context.txt file for complete results
- Use custom output paths (--output) when working with multiple queries
- Use the --terminal flag when you need to see results immediately
- Process output files with other tools (grep, sed, awk) for further filtering
- Combine with `jq` for JSON output processing
