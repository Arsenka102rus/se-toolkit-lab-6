# Task 3 Implementation Plan: The System Agent

## Overview
Extend the documentation agent (Task 2) with a `query_api` tool that enables the agent to communicate with the deployed backend API. The agent must answer both static system facts and data-dependent queries.

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
                │                 │  │  (LMS_API_KEY)      │
                └─────────────────┘  └─────────────────────┘
```

---

## New Tool: `query_api`

### Schema Definition
```json
{
  "type": "function",
  "function": {
    "name": "query_api",
    "description": "Make an HTTP request to the backend LMS API",
    "parameters": {
      "type": "object",
      "properties": {
        "method": {
          "type": "string",
          "description": "HTTP method (GET, POST, etc.)",
          "enum": ["GET", "POST", "PUT", "DELETE"]
        },
        "path": {
          "type": "string",
          "description": "API path (e.g., '/items/', '/analytics/completion-rate')"
        },
        "body": {
          "type": "string",
          "description": "Optional JSON request body"
        }
      },
      "required": ["method", "path"]
    }
  }
}
```

### Implementation Details
- Base URL from `AGENT_API_BASE_URL` env var (default: `http://localhost:42002`)
- Authentication via `LMS_API_KEY` from `.env.docker.secret`
- Returns JSON string with `status_code` and `body`

---

## Environment Variables

### From `.env.agent.secret` (LLM config)
- `LLM_API_KEY` - LLM provider API key
- `LLM_API_BASE` - LLM API endpoint URL
- `LLM_MODEL` - Model name

### From `.env.docker.secret` (Backend config)
- `LMS_API_KEY` - Backend API key for `query_api` auth

### Optional
- `AGENT_API_BASE_URL` - Base URL for `query_api` (default: `http://localhost:42002`)

---

## System Prompt Updates

The system prompt must guide the LLM to:
1. Use `read_file`/`list_files` for wiki documentation questions
2. Use `query_api` for live data questions (item counts, analytics, status codes)
3. Combine tools when debugging errors (query API, then read source code)

Example addition:
```
You also have access to query_api(method, path, body?) for querying the backend API.
- Use query_api for questions about live data (item counts, analytics, status codes)
- Use read_file/list_files for documentation questions
- For debugging questions, you may need to use both: first query_api to see the error, then read_file to examine the source code
```

---

## Benchmark Questions Analysis

| # | Question Type | Tools Needed | Strategy |
|---|---------------|--------------|----------|
| 0-1 | Wiki docs | read_file | Search wiki for branch protection, SSH |
| 2 | Source code | read_file | Read backend/app files for framework |
| 3 | API structure | list_files | List backend routers |
| 4-5 | Live data | query_api | GET /items/, check status codes |
| 6-7 | Debug errors | query_api + read_file | Query endpoint, read source to find bug |
| 8-9 | Architecture | read_file | Read docker-compose, Dockerfile, ETL code |

---

## Testing Strategy

### Test 1: Static System Question
```bash
uv run agent.py "What Python web framework does the backend use?"
```
**Expected:** `read_file` in tool_calls, answer contains "FastAPI"

### Test 2: Data-Dependent Question
```bash
uv run agent.py "How many items are in the database?"
```
**Expected:** `query_api` in tool_calls, answer contains a number

---

## Benchmark Iteration Strategy

1. **First Run:** Run `uv run run_eval.py` and record initial score
2. **Diagnose Failures:** Identify which questions failed and why
3. **Fix Issues:**
   - Tool not called → Improve tool description in schema
   - Wrong arguments → Clarify parameter descriptions
   - Timeout → Reduce max iterations or optimize prompts
4. **Re-run:** Iterate until all 10 questions pass

---

## Timeline

1. ✅ Create this plan
2. ⏳ Add `query_api` tool to agent.py
3. ⏳ Update system prompt
4. ⏳ Update AGENT.md documentation
5. ⏳ Add 2 regression tests
6. ⏳ Run benchmark and iterate
7. ⏳ Submit PR
