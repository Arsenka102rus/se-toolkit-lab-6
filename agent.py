#!/usr/bin/env python3
"""
Agent CLI - System Agent with API Query Tool

This script takes a question as input, uses an agentic loop with tools
(read_file, list_files, query_api) to explore the project wiki and query
the backend API, then returns a structured JSON response.

Usage:
    uv run agent.py "How many items are in the database?"

Output:
    {
      "answer": "...",
      "source": "wiki/...",
      "tool_calls": [...]
    }
"""

import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv, find_dotenv

# Maximum tool calls per question
MAX_TOOL_CALLS = 10

# System prompt for the system agent
SYSTEM_PROMPT = """You are a documentation and system assistant with access to a project wiki and backend API.
You have three tools available:
- list_files(path): List files and directories in a path
- read_file(path): Read the contents of a file
- query_api(method, path, body?): Make HTTP requests to the backend API

Your task is to answer user questions by exploring the wiki and querying the API.

Tool selection guidelines:
1. Use list_files() to explore directory structure
2. Use read_file() to read wiki pages and source code
3. Use query_api() for questions about live data (item counts, analytics, status codes)
4. For debugging questions, use query_api() first to see the error, then read_file() to examine source code

Always cite your sources:
- For wiki/docs: use the file path (e.g., wiki/git-workflow.md)
- For API data: mention the endpoint (e.g., GET /items/)
- For source code: use the file path (e.g., backend/app/main.py)

Be concise but thorough. When you have enough information, provide a final answer."""


def load_config() -> dict:
    """Load configuration from environment variables."""
    script_dir = Path(__file__).parent
    
    # Load LLM config from .env.agent.secret
    agent_env = script_dir / ".env.agent.secret"
    if agent_env.exists():
        load_dotenv(agent_env)
    
    # Also try loading from .env.docker.secret for LMS_API_KEY
    docker_env = script_dir / ".env.docker.secret"
    if docker_env.exists():
        load_dotenv(docker_env, override=False)
    
    config = {
        "api_base": os.getenv("LLM_API_BASE"),
        "api_key": os.getenv("LLM_API_KEY"),
        "model": os.getenv("LLM_MODEL"),
        "lms_api_key": os.getenv("LMS_API_KEY"),
        "agent_api_base_url": os.getenv("AGENT_API_BASE_URL", "http://localhost:42002"),
    }
    
    missing = [key for key, value in config.items() if not value and key in ["api_base", "api_key", "model", "lms_api_key"]]
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


def query_api(method: str, path: str, body: str = None) -> str:
    """Make an HTTP request to the backend API."""
    config = load_config()
    base_url = config["agent_api_base_url"]
    api_key = config["lms_api_key"]
    
    # Validate method
    valid_methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]
    if method.upper() not in valid_methods:
        return json.dumps({"error": f"Invalid method: {method}", "status_code": 400})
    
    # Build URL
    url = f"{base_url}{path}"
    
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": api_key,
    }
    
    print(f"  Querying API: {method} {url}", file=sys.stderr)
    
    try:
        with httpx.Client(timeout=30.0) as client:
            if method.upper() == "GET":
                response = client.get(url, headers=headers)
            elif method.upper() == "POST":
                data = json.loads(body) if body else {}
                response = client.post(url, headers=headers, json=data)
            elif method.upper() == "PUT":
                data = json.loads(body) if body else {}
                response = client.put(url, headers=headers, json=data)
            elif method.upper() == "DELETE":
                response = client.delete(url, headers=headers)
            elif method.upper() == "PATCH":
                data = json.loads(body) if body else {}
                response = client.patch(url, headers=headers, json=data)
            
            result = {
                "status_code": response.status_code,
                "body": response.text[:5000]  # Limit response size
            }
            return json.dumps(result)
            
    except httpx.TimeoutException:
        return json.dumps({"error": "Request timed out", "status_code": 408})
    except httpx.RequestError as e:
        return json.dumps({"error": str(e), "status_code": 0})
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON body: {e}", "status_code": 400})
    except Exception as e:
        return json.dumps({"error": str(e), "status_code": 500})


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
                            "description": "Relative path from project root (e.g., 'wiki/git-workflow.md', 'backend/app/main.py')"
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
                            "description": "Relative directory path from project root (e.g., 'wiki', 'backend/app')"
                        }
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_api",
                "description": "Make an HTTP request to the backend LMS API. Use for questions about live data, item counts, analytics, or API status codes.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "method": {
                            "type": "string",
                            "description": "HTTP method (GET, POST, PUT, DELETE)",
                            "enum": ["GET", "POST", "PUT", "DELETE"]
                        },
                        "path": {
                            "type": "string",
                            "description": "API path (e.g., '/items/', '/analytics/completion-rate')"
                        },
                        "body": {
                            "type": "string",
                            "description": "Optional JSON request body for POST/PUT requests"
                        }
                    },
                    "required": ["method", "path"]
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
    elif name == "query_api":
        return query_api(
            args.get("method", "GET"),
            args.get("path", ""),
            args.get("body")
        )
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
            answer = assistant_message.get("content") or ""
            
            # Extract source from answer (look for wiki/ or backend/ references)
            source = extract_source(answer)
            
            print(f"\nFinal answer received", file=sys.stderr)
            return answer, source, tool_calls_log
    
    # Max iterations reached
    print(f"\nMax iterations ({MAX_TOOL_CALLS}) reached", file=sys.stderr)
    
    # Try to extract an answer from the last response
    answer = assistant_message.get("content") or "Unable to complete the task within the tool call limit."
    source = extract_source(answer)
    
    return answer, source, tool_calls_log


def extract_source(answer: str) -> str:
    """Extract source file reference from the answer."""
    import re
    
    # Look for wiki/ file references
    match = re.search(r'(wiki/[\w\-\.]+)', answer)
    if match:
        return match.group(1)
    
    # Look for backend/ file references
    match = re.search(r'(backend/[\w\-\.\/]+)', answer)
    if match:
        return match.group(1)
    
    # Look for any .md file references
    match = re.search(r'([\w\-]+\.md)', answer)
    if match:
        return f"wiki/{match.group(1)}"
    
    # Look for API endpoint references
    match = re.search(r'((GET|POST|PUT|DELETE)\s+/[\w\-\/]+)', answer)
    if match:
        return match.group(1)
    
    return ""


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
