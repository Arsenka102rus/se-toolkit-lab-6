#!/usr/bin/env python3
"""
Agent CLI - Call an LLM from Code

This script takes a question as input, sends it to an LLM via proxy,
and returns a structured JSON response.

Usage:
    uv run agent.py "What does REST stand for?"

Output:
    {"answer": "Representational State Transfer.", "tool_calls": []}
"""

import json
import os
import sys
from pathlib import Path

import httpx
from dotenv import load_dotenv


def load_config() -> dict:
    """Load configuration from environment variables."""
    # Load .env.agent.secret from the script's directory
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
    
    # Validate required config
    missing = [key for key, value in config.items() if not value]
    if missing:
        print(f"Error: Missing required config: {', '.join(missing)}", file=sys.stderr)
        sys.exit(1)
    
    return config


def call_llm(question: str, config: dict) -> str:
    """
    Send a question to the LLM and return the answer.
    
    Args:
        question: The user's question
        config: Configuration dict with api_base, api_key, model
        
    Returns:
        The LLM's answer text
    """
    api_url = f"{config['api_base']}/chat/completions"
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config['api_key']}",
    }
    
    payload = {
        "model": config["model"],
        "messages": [
            {"role": "user", "content": question}
        ],
        "temperature": 0.7,
    }
    
    print(f"Sending request to {api_url}...", file=sys.stderr)
    print(f"Model: {config['model']}", file=sys.stderr)
    print(f"Question: {question}", file=sys.stderr)
    
    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(api_url, headers=headers, json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            # Extract the answer from the response
            if "choices" in data and len(data["choices"]) > 0:
                answer = data["choices"][0]["message"]["content"]
                print(f"Received response from LLM", file=sys.stderr)
                return answer
            else:
                print(f"Error: Unexpected response format: {data}", file=sys.stderr)
                sys.exit(1)
                
    except httpx.TimeoutException:
        print("Error: Request timed out after 60 seconds", file=sys.stderr)
        sys.exit(1)
    except httpx.RequestError as e:
        print(f"Error: Request failed: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point for the agent CLI."""
    # Check command-line arguments
    if len(sys.argv) != 2:
        print("Usage: uv run agent.py \"<your question>\"", file=sys.stderr)
        sys.exit(1)
    
    question = sys.argv[1]
    
    # Load configuration
    config = load_config()
    
    # Call the LLM
    answer = call_llm(question, config)
    
    # Build the structured response
    response = {
        "answer": answer,
        "tool_calls": []
    }
    
    # Output only valid JSON to stdout
    print(json.dumps(response, ensure_ascii=False))


if __name__ == "__main__":
    main()
