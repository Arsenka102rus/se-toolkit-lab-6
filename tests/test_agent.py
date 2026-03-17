"""
Regression tests for agent.py

Tests verify that the agent outputs valid JSON with required fields.
"""

import json
import subprocess
import sys
from pathlib import Path


def test_agent_output_format():
    """Test that agent.py outputs valid JSON with 'answer' and 'tool_calls' fields."""
    # Path to agent.py (project root)
    project_root = Path(__file__).parent.parent.parent.parent
    agent_path = project_root / "agent.py"
    
    # Run agent with a simple test question
    result = subprocess.run(
        ["uv", "run", str(agent_path), "What is 2+2?"],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(project_root)
    )
    
    # Check exit code
    assert result.returncode == 0, f"Agent failed with: {result.stderr}"
    
    # Parse stdout as JSON (should be only JSON, debug goes to stderr)
    try:
        output = json.loads(result.stdout.strip())
    except json.JSONDecodeError as e:
        raise AssertionError(f"Agent output is not valid JSON: {e}\nStdout: {result.stdout}")
    
    # Verify required fields exist
    assert "answer" in output, "Missing 'answer' field in output"
    assert "tool_calls" in output, "Missing 'tool_calls' field in output"
    
    # Verify field types
    assert isinstance(output["answer"], str), "'answer' should be a string"
    assert isinstance(output["tool_calls"], list), "'tool_calls' should be an array"
    
    # Verify answer is non-empty
    assert len(output["answer"].strip()) > 0, "'answer' field is empty"
    
    print("✓ All checks passed!")
    print(f"  - answer: {output['answer'][:50]}...")
    print(f"  - tool_calls: {output['tool_calls']}")


def test_agent_stderr_separation():
    """Test that debug output goes to stderr, not stdout."""
    project_root = Path(__file__).parent.parent.parent.parent
    agent_path = project_root / "agent.py"
    
    result = subprocess.run(
        ["uv", "run", str(agent_path), "Test question"],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=str(project_root)
    )
    
    # stdout should be valid JSON only
    try:
        json.loads(result.stdout.strip())
    except json.JSONDecodeError as e:
        raise AssertionError(f"stdout contains non-JSON content: {e}")
    
    # stderr should contain debug messages (non-empty for successful run)
    assert len(result.stderr) > 0, "stderr should contain debug messages"
    
    print("✓ Output separation test passed!")


if __name__ == "__main__":
    print("Running agent.py regression tests...\n")
    
    try:
        test_agent_output_format()
        print()
        test_agent_stderr_separation()
        print("\n✅ All regression tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("\n❌ Test timed out after 60 seconds")
        sys.exit(1)
