"""Read git state for proof context. No gitpython dependency — uses subprocess."""

from __future__ import annotations

import subprocess
from hashlib import sha256


def _run_git(repo_path: str | None, *args: str) -> str | None:
    """Run a git command, return stdout or None on failure."""
    cmd = ["git"]
    if repo_path:
        cmd.extend(["-C", repo_path])
    cmd.extend(args)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            return None
        return result.stdout.strip()
    except Exception:
        return None


def is_git_repo(path: str | None = None) -> bool:
    """Check if the path is inside a git repo."""
    return _run_git(path, "rev-parse", "--is-inside-work-tree") == "true"


def get_current_diff(repo_path: str | None = None, file: str = "train.py") -> str | None:
    """Get the git diff for a specific file."""
    return _run_git(repo_path, "diff", "--", file)


def get_diff_hash(repo_path: str | None = None, file: str = "train.py") -> str | None:
    """Get SHA-256 hash of the git diff for a file."""
    diff = get_current_diff(repo_path, file)
    if diff is None:
        return None
    return sha256(diff.encode("utf-8")).hexdigest()


def get_latest_commit_hash(repo_path: str | None = None) -> str | None:
    """Get the latest commit hash."""
    return _run_git(repo_path, "rev-parse", "HEAD")


def get_commit_message(repo_path: str | None = None, commit_hash: str = "HEAD") -> str | None:
    """Get the commit message for a given hash."""
    return _run_git(repo_path, "log", "-1", "--format=%s", commit_hash)
