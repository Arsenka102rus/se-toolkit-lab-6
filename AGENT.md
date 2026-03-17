# Agent Documentation

## Overview

`agent.py` is a Python CLI program that sends questions to an LLM (via the qwen-code-oai-proxy) and returns structured JSON responses.

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

## Usage

### Basic Usage

```bash
uv run agent.py "What does REST stand for?"
```

### Output Format

**stdout** (valid JSON only):
```json
{
  "answer": "REST stands for Representational State Transfer...",
  "tool_calls": []
}
```

**stderr** (debug information):
```
Sending request to http://10.93.26.59:42005/v1/chat/completions...
Model: qwen3-coder-plus
Question: What does REST stand for?
Received response from LLM
```

---

## Configuration

Environment variables are loaded from `.env.agent.secret`:

| Variable | Description | Example |
|----------|-------------|---------|
| `LLM_API_BASE` | Proxy API endpoint | `http://10.93.26.59:42005/v1` |
| `LLM_API_KEY` | API key for authentication | `qwen-key` |
| `LLM_MODEL` | Model to use | `qwen3-coder-plus` |

### Setup

```bash
# Copy the example file
cp .env.agent.example .env.agent.secret

# Edit with your configuration
# (API key must match QWEN_API_KEY in proxy's .env file)
```

---

## Implementation Details

### Request Flow

1. **Parse Arguments**: Read question from command-line argument
2. **Load Config**: Read environment variables from `.env.agent.secret`
3. **Build Request**: Create OpenAI-compatible chat completion payload
4. **Send Request**: POST to `/v1/chat/completions` endpoint
5. **Parse Response**: Extract answer from LLM response
6. **Output JSON**: Print structured response to stdout

### API Request Format

```json
{
  "model": "qwen3-coder-plus",
  "messages": [
    {"role": "user", "content": "What does REST stand for?"}
  ],
  "temperature": 0.7
}
```

### Error Handling

| Error | Exit Code | Output |
|-------|-----------|--------|
| Missing config file | 1 | Error message to stderr |
| Missing environment variables | 1 | Error message to stderr |
| Request timeout (>60s) | 1 | Error message to stderr |
| Network error | 1 | Error message to stderr |
| API error (401, 500, etc.) | 1 | Error message to stderr |
| Success | 0 | JSON to stdout |

---

## Dependencies

- **httpx** - HTTP client for API calls (already in pyproject.toml)
- **python-dotenv** - Load environment variables from `.env` file

Install with:
```bash
uv add python-dotenv
```

---

## Testing

### Manual Testing

```bash
# Simple question
uv run agent.py "What is Python?"

# Complex question
uv run agent.py "Explain the difference between REST and GraphQL"
```

### Regression Test

Run the test suite:
```bash
uv run pytest backend/tests/unit/test_agent.py -v
```

The test verifies:
- JSON output is valid
- `answer` field exists and is non-empty
- `tool_calls` field exists and is an array

---

## File Structure

```
/root/se-toolkit-lab-6/
├── agent.py              # Main CLI program
├── .env.agent.example    # Example environment configuration
├── .env.agent.secret     # Actual environment configuration (git-ignored)
├── pyproject.toml        # Python project dependencies
├── plans/
│   └── task-1.md         # Implementation plan
└── backend/
    └── tests/
        └── unit/
            └── test_agent.py  # Regression tests
```

---

## Next Steps (Tasks 2-3)

In upcoming tasks, the agent will be extended with:
- Tool calling support (populating `tool_calls` array)
- Agentic loop for multi-step reasoning
- Tool execution capabilities (read_file, list_files, query_api)

---

## Troubleshooting

### "401 Unauthorized"
- Ensure `LLM_API_KEY` in `.env.agent.secret` matches `QWEN_API_KEY` in proxy's `.env`

### "Connection refused"
- Ensure the proxy is running: check `docker-compose ps` in qwen-code-oai-proxy
- Check `LLM_API_BASE` points to the correct VM IP and port (10.93.26.59:42005)
- Ensure firewall allows connections on port 42005

### "Request timed out"
- The proxy or LLM may be slow; increase timeout in `call_llm()` function
- Check proxy logs for errors

### Invalid JSON output
- Debug messages go to stderr; only JSON should go to stdout
- Run with `2>/dev/null` to see only JSON output
