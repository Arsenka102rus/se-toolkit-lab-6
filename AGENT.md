# Agent Documentation - System Agent (Task 3)

## Overview

`agent.py` is a Python CLI program that implements an **agentic loop** with three tools (`read_file`, `list_files`, `query_api`) to explore the project wiki, query the backend API, and answer questions with source references.

---

## Architecture

```
┌─────────┐     ┌─────────────────────────────────────────────────────┐
│  User   │ ──▶ │  agent.py (Agentic Loop)                          │
│         │ ◀── │                                                   │
└─────────┘     │  Tools: read_file, list_files, query_api          │
                └─────────────────────────────────────────────────────┘
                          │                    │
                          ▼                    ▼
                ┌─────────────────┐  ┌─────────────────────┐
                │  Wiki Files     │  │  Backend API        │
                │  (read_file)    │  │  (query_api)        │
                │  Source Code    │  │  (LMS_API_KEY)      │
                └─────────────────┘  └─────────────────────┘
```

---

## Usage

### Basic Usage

```bash
uv run agent.py "How many items are in the database?"
```

### Output Format

**stdout** (valid JSON only):
```json
{
  "answer": "There are 42 items in the database.",
  "source": "GET /items/",
  "tool_calls": [
    {
      "tool": "query_api",
      "args": {"method": "GET", "path": "/items/"},
      "result": "{\"status_code\": 200, \"body\": \"[...]\"}"
    }
  ]
}
```

---

## Configuration

Environment variables are loaded from multiple sources:

### From `.env.agent.secret` (LLM config)
| Variable | Description | Example |
|----------|-------------|---------|
| `LLM_API_BASE` | Proxy API endpoint | `http://10.93.26.59:42005/v1` |
| `LLM_API_KEY` | API key for authentication | `qwen-key` |
| `LLM_MODEL` | Model to use | `qwen3-coder-plus` |

### From `.env.docker.secret` (Backend config)
| Variable | Description | Example |
|----------|-------------|---------|
| `LMS_API_KEY` | Backend API key for query_api | `api-key` |

### Optional
| Variable | Description | Default |
|----------|-------------|---------|
| `AGENT_API_BASE_URL` | Base URL for query_api | `http://localhost:42002` |

---

## Tools

### 1. `read_file`

Reads the contents of a file from the project root.

**Parameters:**
- `path` (string): Relative path from project root (e.g., `wiki/git-vscode.md`, `backend/app/main.py`)

**Returns:** File contents as a string, or an error message

**Security:** Rejects paths containing `..` (directory traversal protection)

**Use cases:**
- Reading wiki documentation
- Examining source code for debugging
- Understanding architecture from config files

### 2. `list_files`

Lists files and directories in a directory.

**Parameters:**
- `path` (string): Relative directory path from project root (e.g., `wiki`, `backend/app`)

**Returns:** Newline-separated listing of entries

**Security:** Rejects paths containing `..` (directory traversal protection)

**Use cases:**
- Exploring directory structure
- Finding API router modules
- Discovering available documentation

### 3. `query_api`

Makes HTTP requests to the backend LMS API.

**Parameters:**
- `method` (string): HTTP method (GET, POST, PUT, DELETE)
- `path` (string): API path (e.g., `/items/`, `/analytics/completion-rate`)
- `body` (string, optional): JSON request body for POST/PUT requests

**Returns:** JSON string with `status_code` and `body`

**Authentication:** Uses `LMS_API_KEY` from `.env.docker.secret` via `X-API-Key` header

**Use cases:**
- Getting item counts from database
- Checking API status codes
- Debugging API errors
- Querying analytics endpoints

---

## Agentic Loop

The agentic loop works as follows:

1. **Initialize**: Create messages array with system prompt and user question
2. **Call LLM**: Send messages + tool schemas to the LLM
3. **Check Response**:
   - If `tool_calls` present → execute each tool, append results, repeat
   - If no `tool_calls` → extract answer and source, return
4. **Max Iterations**: Stop after 10 tool calls to prevent infinite loops

### Tool Selection Strategy

The LLM is guided to select tools based on question type:

| Question Type | Tool to Use | Example |
|---------------|-------------|---------|
| Wiki documentation | `read_file`, `list_files` | "How do I resolve a merge conflict?" |
| Source code inquiry | `read_file` | "What framework does the backend use?" |
| Live data | `query_api` | "How many items are in the database?" |
| API status codes | `query_api` | "What status code for unauthenticated request?" |
| Debug errors | `query_api` + `read_file` | "Why does /analytics/top-learners crash?" |
| Architecture | `read_file` | "Explain the request journey from browser to DB" |

### System Prompt

The system prompt instructs the LLM to:
- Use `list_files()` to explore directory structure
- Use `read_file()` to read wiki pages and source code
- Use `query_api()` for live data questions
- For debugging: first `query_api()` to see the error, then `read_file()` to examine source
- Always cite sources (file paths or API endpoints)

---

## Implementation Details

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

The `extract_source()` function uses regex to find references in the answer:
- `wiki/` file paths
- `backend/` source paths
- API endpoint references (e.g., `GET /items/`)

### API Authentication

```python
headers = {
    "Content-Type": "application/json",
    "X-API-Key": api_key,  # LMS_API_KEY from .env.docker.secret
}
```

---

## Error Handling

| Error | Exit Code | Output |
|-------|-----------|--------|
| Missing config file | 1 | Error message to stderr |
| Missing environment variables | 1 | Error message to stderr |
| Request timeout (>60s) | 1 | Error message to stderr |
| Network error | 1 | Error message to stderr |
| API error (401, 500, etc.) | 0 | Error in tool result |
| Unsafe path detected | 0 | Error in tool result |
| Success | 0 | JSON to stdout |

---

## Testing

### Manual Testing

```bash
# Wiki documentation question
uv run agent.py "How do you resolve a merge conflict?"

# Source code question
uv run agent.py "What Python framework does the backend use?"

# Live data question
uv run agent.py "How many items are in the database?"

# API status code question
uv run agent.py "What status code for unauthenticated /items/ request?"
```

### Regression Tests

Run the test suite:
```bash
uv run pytest tests/test_agent.py -v
```

Tests verify:
- JSON output is valid
- `answer`, `source`, and `tool_calls` fields exist
- Correct tool is used for each question type
- Answers contain expected content (e.g., "FastAPI", numbers)

---

## Benchmark Performance

The agent is evaluated against 10 benchmark questions:

| # | Question | Tool(s) Required | Status |
|---|----------|------------------|--------|
| 0 | Branch protection on GitHub | read_file | ✅ |
| 1 | SSH connection steps | read_file | ✅ |
| 2 | Python web framework | read_file | ✅ |
| 3 | API router modules | list_files | ✅ |
| 4 | Item count in database | query_api | ✅ |
| 5 | Status code without auth | query_api | ✅ |
| 6 | ZeroDivisionError bug | query_api + read_file | ✅ |
| 7 | TypeError in top-learners | query_api + read_file | ✅ |
| 8 | Request journey (architecture) | read_file | ✅ |
| 9 | ETL idempotency | read_file | ✅ |

### Lessons Learned

1. **Tool descriptions matter**: Vague descriptions lead to wrong tool selection. Be explicit about when to use each tool.

2. **Content truncation**: Large files get truncated. The agent needs to handle partial content gracefully.

3. **API error handling**: The `query_api` tool must return structured errors so the LLM can understand what went wrong.

4. **Source extraction**: Regex-based source extraction works well for file paths but may miss API endpoint references in some answers.

5. **Max iterations**: 10 iterations is usually enough, but complex debugging questions may need more back-and-forth.

---

## File Structure

```
/root/se-toolkit-lab-6/
├── agent.py              # Main CLI program with agentic loop
├── .env.agent.secret     # LLM environment configuration
├── .env.docker.secret    # Backend API configuration
├── AGENT.md              # This documentation
├── plans/
│   └── task-3.md         # Implementation plan
├── wiki/                 # Project wiki
├── backend/              # Backend source code
└── tests/
    └── test_agent.py     # Regression tests
```

---

## Troubleshooting

### "401 Unauthorized" from API
- Ensure `LMS_API_KEY` in `.env.docker.secret` matches the backend's expected key
- Check the `X-API-Key` header is being sent

### "Connection refused" from API
- Ensure backend is running: `docker-compose ps`
- Check `AGENT_API_BASE_URL` points to correct port (42002 for Caddy)

### Agent doesn't use query_api for data questions
- Improve system prompt to clarify when to use query_api
- Add examples to tool description

### Agent times out
- Reduce max iterations from 10
- Check LLM proxy is responsive

### "NoneType" errors
- Handle null content from LLM: use `(msg.get("content") or "")` instead of `msg.get("content", "")`

---

## Word Count: ~1,200 words
