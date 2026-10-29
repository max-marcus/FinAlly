#!/usr/bin/env python3
"""On a completed stop with uncommitted changes, ask the session to run change-reviewer."""

import json
import os
import subprocess
import sys

MESSAGE = (
    "Run the change-reviewer subagent defined in .claude/agents/reviewer.md. "
    "Have it review all changes since the last commit. "
    "Do not review the changes yourself."
)


def worktree_has_changes() -> bool:
    """Return True when git reports staged, unstaged, or untracked changes."""
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.environ.get("CURSOR_PROJECT_DIR") or None
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return result.returncode == 0 and bool(result.stdout.strip())


def main() -> None:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError:
        return

    if not isinstance(data, dict):
        return
    if data.get("status", "completed") != "completed":
        return
    if data.get("loop_count", 0) not in (0, "0"):
        return
    if data.get("stop_hook_active") is True:
        return
    if not worktree_has_changes():
        return

    json.dump(
        {
            "followup_message": MESSAGE,
            "hookSpecificOutput": {
                "hookEventName": "Stop",
                "additionalContext": MESSAGE,
            },
        },
        sys.stdout,
    )
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
