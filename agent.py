#!/usr/bin/env python3
"""
Agent CLI - Documentation Agent with Agentic Loop

This script takes a question as input, uses an agentic loop with tools
(read_file, list_files) to query the project wiki, and returns a structured
JSON response with answer, source, and tool_calls.

Usage:
    uv run agent.py "How do you resolve a merge conflict?"

Output:
    {
      "answer": "...",
      "source": "wiki/git-workflow.md",
      "tool_calls": [...]
    }
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

# Maximum tool calls per question
MAX_TOOL_CALLS = 10

# System prompt for the documentation agent
SYSTEM_PROMPT = """You are a documentation assistant with access to a project wiki.
You have two tools available:
- list_files(path): List files and directories in a path
- read_file(path): Read the contents of a file

Your task is to answer user questions by exploring the wiki.
1. Use list_files() to explore directory structure
2. Use read_file() to read relevant wiki pages
3. Always cite your sources using the file path (e.g., wiki/git-workflow.md)
4. When you have enough information, provide a final answer with the source

Be concise but thorough. Always include the source file path in your answer."""


def load_config() -> dict:
    """Load configuration from environment variables."""
    script_dir = Path(__file__).parent
    env_file = script_dir / ".env.agent.secret"
    
    if not env_file.exists():
        print(f"Error: {env_file} not found", file=sys.stderr)
        print("Copy .env.agent.example to .env.agent.secret and configure it", file=sys.stderr)
        sys.exit(1)
    
    load_dotenv(env_file)
    
    config = {
        "api_base": os.getenv("LLM_API_BASE"),
        "api_key": os.getenv("LLM_API_KEY"),
        "model": os.getenv("LLM_MODEL"),
    }
    
    missing = [key for key, value in config.items() if not value]
    if missing:
        print(f"Error: Missing required config: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)
    
    return config


def is_safe_path(path: str) -> bool:
    """Check if path is safe (no directory traversal)."""
    if ".." in path:
        return False
    if path.startswith("/"):
        return False
    return True


def read_file(path: str) -> str:
    """Read the contents of a file."""
    if not is_safe_path(path):
        return f"Error: Unsafe path detected (directory traversal not allowed)"
    
    script_dir = Path(__file__).parent
    file_path = script_dir / path
    
    if not file_path.exists():
        return f"Error: File not found: {path}"
    
    if not file_path.is_file():
        return f"Error: Not a file: {path}"
    
    try:
        content = file_path.read_text()
        # Limit content length to avoid token limits
        max_content = 8000
        if len(content) > max_content:
            content = content[:max_content] + "\n... (content truncated)"
        return content
    except Exception as e:
        return f"Error reading file: {e}"


def list_files(path: str) -> str:
    """List files and directories in a path."""
    if not is_safe_path(path):
        return f"Error: Unsafe path detected (directory traversal not allowed)"
    
    script_dir = Path(__file__).parent
    dir_path = script_dir / path
    
    if not dir_path.exists():
        return f"Error: Directory not found: {path}"
    
    if not dir_path.is_dir():
        return f"Error: Not a directory: {path}"
    
    try:
        entries = sorted([e.name for e in dir_path.iterdir()])
        return "\n".join(entries)
    except Exception as e:
        return f"Error listing directory: {e}"


def get_tool_schemas() -> list[dict]:
    """Return the tool/function schemas for the LLM."""
    return [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read the contents of a file at the given path",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path from project root (e.g., 'wiki/git-workflow.md')"
                        }
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List files and directories in a directory",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative directory path from project root (e.g., 'wiki')"
                        }
                    },
                    "required": ["path"]
                }
            }
        }
    ]


def execute_tool(name: str, args: dict) -> str:
    """Execute a tool and return the result."""
    print(f"  Executing tool: {name}({args})", file=sys.stderr)
    
    if name == "read_file":
        return read_file(args.get("path", ""))
    elif name == "list_files":
        return list_files(args.get("path", ""))
    else:
        return f"Error: Unknown tool: {name}"


def call_llm_with_tools(messages: list[dict], config: dict, tools: list[dict]) -> dict:
    """Call the LLM with tool support."""
    api_url = f"{config['api_base']}/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config['api_key']}",
    }
    
    payload = {
        "model": config["model"],
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
        "temperature": 0.7,
    }
    
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(api_url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()
    except httpx.TimeoutException:
        print("Error: Request timed out after 60 seconds", file=sys.stderr)
        sys.exit(1)
    except httpx.RequestError as e:
        print(f"Error: Request failed: {e}", file=sys.stderr)
        sys.exit(1)


def run_agentic_loop(question: str, config: dict) -> tuple[str, str, list]:
    """
    Run the agentic loop to answer a question using tools.
    
    Returns:
        tuple: (answer, source, tool_calls_log)
    """
    tools = get_tool_schemas()
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question}
    ]
    
    tool_calls_log = []
    
    print(f"Starting agentic loop for: {question}", file=sys.stderr)
    
    for iteration in range(MAX_TOOL_CALLS):
        print(f"\n--- Iteration {iteration + 1} ---", file=sys.stderr)
        
        # Call LLM
        print("Calling LLM...", file=sys.stderr)
        response = call_llm_with_tools(messages, config, tools)
        
        # Get the assistant message
        assistant_message = response["choices"][0]["message"]
        
        # Check for tool calls
        tool_calls = assistant_message.get("tool_calls", [])
        
        if tool_calls:
            # Add assistant message to history
            messages.append(assistant_message)
            
            # Execute each tool call
            for tool_call in tool_calls:
                function = tool_call["function"]
                name = function["name"]
                args = json.loads(function["arguments"])
                
                # Execute the tool
                result = execute_tool(name, args)
                
                # Log the tool call
                tool_calls_log.append({
                    "tool": name,
                    "args": args,
                    "result": result
                })
                
                # Add tool result to messages
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": result
                })
                
                print(f"  Tool result: {result[:100]}...", file=sys.stderr)
        else:
            # No tool calls - we have the final answer
            answer = assistant_message.get("content", "")
            
            # Extract source from answer (look for wiki/ references)
            source = extract_source(answer)
            
            print(f"\nFinal answer received", file=sys.stderr)
            return answer, source, tool_calls_log
    
    # Max iterations reached
    print(f"\nMax iterations ({MAX_TOOL_CALLS}) reached", file=sys.stderr)
    
    # Try to extract an answer from the last response
    answer = assistant_message.get("content", "Unable to complete the task within the tool call limit.")
    source = extract_source(answer)
    
    return answer, source, tool_calls_log


def extract_source(answer: str) -> str:
    """Extract source file reference from the answer."""
    import re
    
    # Look for wiki/ file references
    match = re.search(r'(wiki/[\w\-\.]+)', answer)
    if match:
        return match.group(1)
    
    # Look for any .md file references
    match = re.search(r'([\w\-]+\.md)', answer)
    if match:
        return f"wiki/{match.group(1)}"
    
    return "wiki/"


def main():
    """Main entry point for the agent CLI."""
    if len(sys.argv) != 2:
        print("Usage: uv run agent.py \"<your question>\"", file=sys.stderr)
        sys.exit(1)
    
    question = sys.argv[1]
    
    # Load configuration
    config = load_config()
    
    # Run the agentic loop
    answer, source, tool_calls = run_agentic_loop(question, config)
    
    # Build the structured response
    response = {
        "answer": answer,
        "source": source,
        "tool_calls": tool_calls
    }
    
    # Output only valid JSON to stdout
    print(json.dumps(response, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
