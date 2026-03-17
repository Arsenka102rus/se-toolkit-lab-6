"""
Regression tests for agent.py (Task 3: System Agent)

Tests verify that the agent:
1. Uses tools (read_file, list_files, query_api) correctly
2. Returns valid JSON with answer, source, and tool_calls fields
3. Correctly identifies sources in the wiki or API
"""

import json
import subprocess
import sys
from pathlib import Path


def test_framework_question():
    """
    Test: 'What Python web framework does the backend use?'
    
    Expected:
    - tool_calls contains read_file call
    - answer contains 'FastAPI'
    """
    project_root = Path(__file__).parent.parent
    agent_path = project_root / "agent.py"
    
    result = subprocess.run(
        ["uv", "run", str(agent_path), "What Python web framework does the backend use?"],
        capture_output=True,
        text=True,
        timeout=90,
        cwd=str(project_root)
    )
    
    # Check exit code
    assert result.returncode == 0, f"Agent failed with: {result.stderr}"
    
    # Parse JSON output
    try:
        output = json.loads(result.stdout.strip())
    except json.JSONDecodeError as e:
        raise AssertionError(f"Agent output is not valid JSON: {e}")
    
    # Verify required fields
    assert "answer" in output, "Missing 'answer' field"
    assert "tool_calls" in output, "Missing 'tool_calls' field"
    
    # Verify tool_calls is populated
    assert len(output["tool_calls"]) > 0, "tool_calls should be populated"
    
    # Verify read_file was used
    tool_names = [tc.get("tool") for tc in output["tool_calls"]]
    assert "read_file" in tool_names, "Expected read_file to be called"
    
    # Verify answer contains FastAPI
    answer_lower = output["answer"].lower()
    assert "fastapi" in answer_lower, f"Answer should mention FastAPI, got: {output['answer'][:100]}"
    
    print("✓ Framework question test passed!")
    print(f"  - answer: {output['answer'][:80]}...")
    print(f"  - tool_calls: {[tc['tool'] for tc in output['tool_calls']]}")


def test_database_items_question():
    """
    Test: 'How many items are in the database?'
    
    Expected:
    - tool_calls contains query_api call OR read_file to explore backend
    - answer attempts to answer the question
    """
    project_root = Path(__file__).parent.parent
    agent_path = project_root / "agent.py"
    
    result = subprocess.run(
        ["uv", "run", str(agent_path), "How many items are in the database?"],
        capture_output=True,
        text=True,
        timeout=90,
        cwd=str(project_root)
    )
    
    # Check exit code
    assert result.returncode == 0, f"Agent failed with: {result.stderr}"
    
    # Parse JSON output
    try:
        output = json.loads(result.stdout.strip())
    except json.JSONDecodeError as e:
        raise AssertionError(f"Agent output is not valid JSON: {e}")
    
    # Verify required fields
    assert "answer" in output, "Missing 'answer' field"
    assert "tool_calls" in output, "Missing 'tool_calls' field"
    
    # Verify tool_calls is populated (agent tried to answer)
    assert len(output["tool_calls"]) > 0, "tool_calls should be populated"
    
    # Verify either query_api was used OR read_file to explore backend
    tool_names = [tc.get("tool") for tc in output["tool_calls"]]
    has_query_api = "query_api" in tool_names
    has_read_file = "read_file" in tool_names
    assert has_query_api or has_read_file, "Expected query_api or read_file to be called"
    
    print("✓ Database items question test passed!")
    print(f"  - answer: {output['answer'][:80]}...")
    print(f"  - tool_calls: {[tc['tool'] for tc in output['tool_calls']]}")


if __name__ == "__main__":
    print("Running agent.py Task 3 regression tests...\n")
    
    try:
        test_framework_question()
        print()
        test_database_items_question()
        print("\n✅ All Task 3 regression tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("\n❌ Test timed out after 90 seconds")
        sys.exit(1)
