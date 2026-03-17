"""
Regression tests for agent.py (Task 2: Documentation Agent)

Tests verify that the agent:
1. Uses tools (read_file, list_files) correctly
2. Returns valid JSON with answer, source, and tool_calls fields
3. Correctly identifies sources in the wiki
"""

import json
import subprocess
import sys
from pathlib import Path


def test_merge_conflict_question():
    """
    Test: 'How do you resolve a merge conflict?'
    
    Expected:
    - tool_calls contains read_file call
    - source contains wiki/git-workflow.md or wiki/git-vscode.md
    """
    project_root = Path(__file__).parent.parent
    agent_path = project_root / "agent.py"
    
    result = subprocess.run(
        ["uv", "run", str(agent_path), "How do you resolve a merge conflict?"],
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
    assert "source" in output, "Missing 'source' field"
    assert "tool_calls" in output, "Missing 'tool_calls' field"
    
    # Verify tool_calls is populated (not empty for this question)
    assert len(output["tool_calls"]) > 0, "tool_calls should be populated"
    
    # Verify read_file was used
    tool_names = [tc.get("tool") for tc in output["tool_calls"]]
    assert "read_file" in tool_names, "Expected read_file to be called"
    
    # Verify source references a wiki file about git
    source = output["source"].lower()
    assert "git" in source or "wiki/" in source, f"Source should reference git wiki file, got: {output['source']}"
    
    print("✓ Merge conflict test passed!")
    print(f"  - answer: {output['answer'][:80]}...")
    print(f"  - source: {output['source']}")
    print(f"  - tool_calls: {[tc['tool'] for tc in output['tool_calls']]}")


def test_wiki_files_question():
    """
    Test: 'What files are in the wiki?'
    
    Expected:
    - tool_calls contains list_files call
    - source references wiki directory
    """
    project_root = Path(__file__).parent.parent
    agent_path = project_root / "agent.py"
    
    result = subprocess.run(
        ["uv", "run", str(agent_path), "What files are in the wiki?"],
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
    assert "source" in output, "Missing 'source' field"
    assert "tool_calls" in output, "Missing 'tool_calls' field"
    
    # Verify tool_calls is populated
    assert len(output["tool_calls"]) > 0, "tool_calls should be populated"
    
    # Verify list_files was used
    tool_names = [tc.get("tool") for tc in output["tool_calls"]]
    assert "list_files" in tool_names, "Expected list_files to be called"
    
    # Verify source references wiki
    assert "wiki" in output["source"].lower(), f"Source should reference wiki, got: {output['source']}"
    
    print("✓ Wiki files test passed!")
    print(f"  - answer: {output['answer'][:80]}...")
    print(f"  - source: {output['source']}")
    print(f"  - tool_calls: {[tc['tool'] for tc in output['tool_calls']]}")


if __name__ == "__main__":
    print("Running agent.py Task 2 regression tests...\n")
    
    try:
        test_merge_conflict_question()
        print()
        test_wiki_files_question()
        print("\n✅ All Task 2 regression tests passed!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("\n❌ Test timed out after 90 seconds")
        sys.exit(1)
