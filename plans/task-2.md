# Task 2 Implementation Plan: The Documentation Agent

## Overview
Build an agentic loop that allows an LLM to use tools (`read_file`, `list_files`) to navigate and query the project wiki, then return answers with source references.

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

## Tool Definitions

### 1. `read_file`
**Schema:**
```json
{
  "type": "function",
  "function": {
    "name": "read_file",
    "description": "Read the contents of a file",
    "parameters": {
      "type": "object",
      "properties": {
        "path": {"type": "string", "description": "Relative path from project root"}
      },
      "required": ["path"]
    }
  }
}
```

**Implementation:**
- Read file from project root
- Security: Reject paths with `../` (directory traversal)
- Return file contents or error message

### 2. `list_files`
**Schema:**
```json
{
  "type": "function",
  "function": {
    "name": "list_files",
    "description": "List files and directories in a path",
    "parameters": {
      "type": "object",
      "properties": {
        "path": {"type": "string", "description": "Relative directory path from project root"}
      },
      "required": ["path"]
    }
  }
}
```

**Implementation:**
- List directory entries from project root
- Security: Reject paths with `../`
- Return newline-separated listing

---

## Agentic Loop Design

```python
def run_agentic_loop(question: str) -> tuple[str, str, list]:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question}
    ]
    
    tool_calls_log = []
    max_iterations = 10
    
    for _ in range(max_iterations):
        # Call LLM with messages + tool schemas
        response = call_llm_with_tools(messages, tools)
        
        # Check for tool calls
        if response has tool_calls:
            for tool_call in tool_calls:
                # Execute tool
                result = execute_tool(tool_call)
                tool_calls_log.append({...})
                
                # Append tool result to messages
                messages.append({"role": "tool", ...})
        else:
            # Final answer received
            answer = extract_answer(response)
            source = extract_source(answer, messages)
            return answer, source, tool_calls_log
    
    # Max iterations reached
    return partial_answer, best_source, tool_calls_log
```

---

## System Prompt Strategy

The system prompt will instruct the LLM to:
1. Use `list_files` to explore the wiki directory structure
2. Use `read_file` to read relevant wiki pages
3. Provide a `source` field referencing the wiki file/section
4. Stop calling tools when enough information is gathered

Example:
```
You are a documentation assistant. You have access to a project wiki.
Use list_files() to explore directories and read_file() to read content.
Always cite your sources using the file path (e.g., wiki/git-workflow.md).
```

---

## Path Security

To prevent directory traversal attacks:
```python
def is_safe_path(path: str) -> bool:
    # Reject any path containing ..
    if ".." in path:
        return False
    # Ensure path doesn't start with /
    if path.startswith("/"):
        return False
    return True
```

---

## Output Format

```json
{
  "answer": "Edit the conflicting file, choose which changes to keep...",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {
      "tool": "list_files",
      "args": {"path": "wiki"},
      "result": "git-workflow.md\n..."
    },
    {
      "tool": "read_file",
      "args": {"path": "wiki/git-workflow.md"},
      "result": "..."
    }
  ]
}
```

---

## Testing Strategy

### Test 1: Merge Conflict Question
```bash
uv run agent.py "How do you resolve a merge conflict?"
```
**Expected:**
- `tool_calls` contains `read_file` call
- `source` contains `wiki/git-workflow.md`

### Test 2: Wiki Files Question
```bash
uv run agent.py "What files are in the wiki?"
```
**Expected:**
- `tool_calls` contains `list_files` call
- `source` may reference wiki directory

---

## Timeline

1. ✅ Create this plan
2. ⏳ Update agent.py with tools and agentic loop
3. ⏳ Update AGENT.md documentation
4. ⏳ Add 2 regression tests
5. ⏳ Test end-to-end
6. ⏳ Submit PR
