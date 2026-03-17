# Agent Documentation

## Overview

`agent.py` is a Python CLI program that implements an **agentic loop** with tools (`read_file`, `list_files`) to explore the project wiki and answer questions with source references.

---

## Architecture

```
┌─────────┐     ┌─────────────────────────────────────────────────────┐
│  User   │ ──▶ │  agent.py (Agentic Loop)                          │
│         │ ◀── │                                                   │
└─────────┘     │  1. Send question + tool schemas to LLM           │
                │  2. If tool_calls → execute tools, repeat         │
                │  3. If final answer → output JSON with source     │
                └─────────────────────────────────────────────────────┘
                          │                    │
                          ▼                    ▼
                ┌─────────────────┐  ┌─────────────────────┐
                │  read_file      │  │  list_files         │
                │  (wiki/*.md)    │  │  (wiki/)            │
                └─────────────────┘  └─────────────────────┘
```

---

## Usage

### Basic Usage

```bash
uv run agent.py "How do you resolve a merge conflict?"
```

### Output Format

**stdout** (valid JSON only):
```json
{
  "answer": "To resolve a merge conflict, open the conflicting file in VS Code...",
  "source": "wiki/git-vscode.md",
  "tool_calls": [
    {
      "tool": "list_files",
      "args": {"path": "wiki"},
      "result": "git-vscode.md\ngit-workflow.md\n..."
    },
    {
      "tool": "read_file",
      "args": {"path": "wiki/git-vscode.md"},
      "result": "# Git in VS Code\n..."
    }
  ]
}
```

**stderr** (debug information):
```
Starting agentic loop for: How do you resolve a merge conflict?

--- Iteration 1 ---
Calling LLM...
  Executing tool: list_files({'path': 'wiki'})
  Tool result: git-vscode.md...

--- Iteration 2 ---
Calling LLM...
  Executing tool: read_file({'path': 'wiki/git-vscode.md'})
  Tool result: # Git in VS Code...

Final answer received
```

---

## Configuration

Environment variables are loaded from `.env.agent.secret`:

| Variable | Description | Example |
|----------|-------------|---------|
| `LLM_API_BASE` | Proxy API endpoint | `http://10.93.26.59:42005/v1` |
| `LLM_API_KEY` | API key for authentication | `qwen-key` |
| `LLM_MODEL` | Model to use | `qwen3-coder-plus` |

---

## Tools

### 1. `read_file`

Reads the contents of a file from the project root.

**Parameters:**
- `path` (string): Relative path from project root (e.g., `wiki/git-vscode.md`)

**Returns:** File contents as a string, or an error message

**Security:** Rejects paths containing `..` (directory traversal protection)

### 2. `list_files`

Lists files and directories in a directory.

**Parameters:**
- `path` (string): Relative directory path from project root (e.g., `wiki`)

**Returns:** Newline-separated listing of entries

**Security:** Rejects paths containing `..` (directory traversal protection)

---

## Agentic Loop

The agentic loop works as follows:

1. **Initialize**: Create messages array with system prompt and user question
2. **Call LLM**: Send messages + tool schemas to the LLM
3. **Check Response**:
   - If `tool_calls` present → execute each tool, append results, repeat
   - If no `tool_calls` → extract answer and source, return
4. **Max Iterations**: Stop after 10 tool calls to prevent infinite loops

### System Prompt

The system prompt instructs the LLM to:
- Use `list_files()` to explore directory structure
- Use `read_file()` to read relevant wiki pages
- Always cite sources using file paths
- Stop calling tools when enough information is gathered

---

## Implementation Details

### Tool Schemas

Tools are defined as OpenAI-compatible function schemas:

```json
{
  "type": "function",
  "function": {
    "name": "read_file",
    "description": "Read the contents of a file",
    "parameters": {
      "type": "object",
      "properties": {
        "path": {"type": "string"}
      },
      "required": ["path"]
    }
  }
}
```

### Path Security

```python
def is_safe_path(path: str) -> bool:
    if ".." in path:
        return False
    if path.startswith("/"):
        return False
    return True
```

### Source Extraction

The `extract_source()` function uses regex to find wiki file references in the answer:
```python
import re
match = re.search(r'(wiki/[\w\-\.]+)', answer)
```

---

## Error Handling

| Error | Exit Code | Output |
|-------|-----------|--------|
| Missing config file | 1 | Error message to stderr |
| Missing environment variables | 1 | Error message to stderr |
| Request timeout (>60s) | 1 | Error message to stderr |
| Network error | 1 | Error message to stderr |
| API error (401, 500, etc.) | 1 | Error message to stderr |
| Unsafe path detected | 0 | Error in tool result |
| Success | 0 | JSON to stdout |

---

## Testing

### Manual Testing

```bash
# Question about merge conflicts
uv run agent.py "How do you resolve a merge conflict?"

# Question about wiki structure
uv run agent.py "What files are in the wiki?"
```

### Regression Tests

Run the test suite:
```bash
uv run pytest tests/test_agent.py -v
```

Tests verify:
- JSON output is valid
- `answer`, `source`, and `tool_calls` fields exist
- Tool calls are populated when tools are used
- Source references wiki files

---

## File Structure

```
/root/se-toolkit-lab-6/
├── agent.py              # Main CLI program with agentic loop
├── .env.agent.secret     # Environment configuration
├── AGENT.md              # This documentation
├── plans/
│   └── task-2.md         # Implementation plan
├── wiki/                 # Project wiki
│   ├── git-vscode.md
│   ├── git-workflow.md
│   └── ...
└── tests/
    └── test_agent.py     # Regression tests
```

---

## Troubleshooting

### "401 Unauthorized"
- Ensure `LLM_API_KEY` matches `QWEN_API_KEY` in proxy's `.env`

### "Connection refused"
- Ensure proxy is running on the configured port
- Check firewall allows connections

### Agent keeps calling tools without answering
- The LLM may need a clearer system prompt
- Check that wiki files contain relevant information

### "Unsafe path detected"
- The agent tried to access a path with `..`
- This is a security feature to prevent directory traversal
