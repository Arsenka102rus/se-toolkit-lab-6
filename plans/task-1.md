# Task 1 Implementation Plan: Call an LLM from Code

## Overview
Build a Python CLI program (`agent.py`) that takes a question as input, sends it to an LLM via the qwen-code-oai-proxy, and returns a structured JSON response.

---

## Architecture

```
┌─────────┐     ┌───────────┐     ┌─────────────────────┐     ┌──────────────┐
│  User   │ ──▶ │ agent.py  │ ──▶ │ qwen-code-oai-proxy │ ──▶ │ Qwen 3 LLM   │
│         │ ◀── │           │ ◀── │  (10.93.26.59:42005)│ ◀── │              │
└─────────┘     └───────────┘     └─────────────────────┘     └──────────────┘
                      │
                      ▼
              JSON Output:
              {
                "answer": "...",
                "tool_calls": []
              }
```

---

## LLM Provider & Model

- **Provider**: Local qwen-code-oai-proxy (running on VM at 10.93.26.59:42005)
- **Model**: `qwen3-coder-plus`
- **API Endpoint**: `http://10.93.26.59:42005/v1/chat/completions`
- **Authentication**: API key `qwen-key` (matches proxy configuration)

---

## Agent Structure

### File: `agent.py` (in project root)

```
agent.py
├── Shebang (#!/usr/bin/env python3)
├── Imports (os, sys, json, httpx, dotenv)
├── Load environment from .env.agent.secret
├── Main function:
│   ├── Parse command-line argument (the question)
│   ├── Build API request to proxy
│   ├── Send POST request to /chat/completions
│   ├── Parse LLM response
│   ├── Format output as JSON: {"answer": "...", "tool_calls": []}
│   └── Print JSON to stdout, debug info to stderr
└── Entry point (if __name__ == "__main__")
```

### Key Implementation Details

1. **Environment Variables** (from `.env.agent.secret`):
   - `LLM_API_BASE` - Proxy endpoint base URL
   - `LLM_API_KEY` - API key for authentication
   - `LLM_MODEL` - Model name to use

2. **API Request Format** (OpenAI-compatible):
   ```json
   {
     "model": "qwen3-coder-plus",
     "messages": [
       {"role": "user", "content": "What does REST stand for?"}
     ]
   }
   ```

3. **Output Format**:
   - **stdout**: Only valid JSON with `answer` and `tool_calls` fields
   - **stderr**: All debug/progress messages
   - **Exit code**: 0 on success, non-zero on error

---

## Dependencies

Using existing project dependencies (already in pyproject.toml):
- `httpx` - HTTP client (already installed)
- `pydantic-settings` or `python-dotenv` - Load environment variables

---

## Testing Strategy

### Manual Testing
```bash
uv run agent.py "What does REST stand for?"
```

Expected output:
```json
{"answer": "Representational State Transfer.", "tool_calls": []}
```

### Regression Test
Create a test in `backend/tests/unit/test_agent.py` that:
1. Runs `agent.py` with a test question
2. Parses the JSON output
3. Verifies `answer` field exists and is non-empty
4. Verifies `tool_calls` field exists and is an array

---

## Git Workflow

1. Create issue: `[Task 1] Call an LLM from Code`
2. Create branch: `feature/task-1-llm-agent`
3. Commit plan first: `docs: add task-1 implementation plan`
4. Implement and commit code: `feat: add agent.py CLI for LLM calls`
5. Add documentation: `docs: add AGENT.md`
6. Add test: `test: add task-1 regression test`
7. Create PR with `Closes #<issue-number>`
8. Get partner approval and merge

---

## Potential Issues & Solutions

| Issue | Solution |
|-------|----------|
| Proxy not running | Start with `docker-compose up` in qwen-code-oai-proxy |
| Timeout (>60s) | Check proxy logs, ensure model is available |
| Invalid JSON output | Ensure only JSON goes to stdout, debug to stderr |
| API key errors | Verify .env.agent.secret matches proxy config |
| Connection refused | Check firewall allows port 42005, verify VM IP |

---

## Timeline

1. ✅ Create this plan
2. ⏳ Implement `agent.py`
3. ⏳ Write `AGENT.md` documentation
4. ⏳ Create regression test
5. ⏳ Test end-to-end
6. ⏳ Submit PR
