"""Tests for git integration."""

import os
import subprocess
import tempfile

from verdicto_autoresearch.git_integration import (
    get_diff_hash,
    get_latest_commit_hash,
    is_git_repo,
)


def test_not_git_repo() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        assert is_git_repo(tmpdir) is False
        assert get_latest_commit_hash(tmpdir) is None
        assert get_diff_hash(tmpdir) is None


def test_is_git_repo_with_real_repo() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(["git", "init", tmpdir], capture_output=True)
        subprocess.run(
            ["git", "-C", tmpdir, "commit", "--allow-empty", "-m", "init"],
            capture_output=True,
            env={**os.environ, "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "t@t",
                 "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "t@t"},
        )
        assert is_git_repo(tmpdir) is True
        commit = get_latest_commit_hash(tmpdir)
        assert commit is not None
        assert len(commit) == 40


def test_diff_hash_deterministic() -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        subprocess.run(["git", "init", tmpdir], capture_output=True)
        env = {**os.environ, "GIT_AUTHOR_NAME": "test", "GIT_AUTHOR_EMAIL": "t@t",
               "GIT_COMMITTER_NAME": "test", "GIT_COMMITTER_EMAIL": "t@t"}

        filepath = os.path.join(tmpdir, "train.py")
        with open(filepath, "w") as f:
            f.write("lr = 0.001\n")
        subprocess.run(["git", "-C", tmpdir, "add", "train.py"], capture_output=True)
        subprocess.run(["git", "-C", tmpdir, "commit", "-m", "init"], capture_output=True, env=env)

        with open(filepath, "w") as f:
            f.write("lr = 0.003\n")

        h1 = get_diff_hash(tmpdir, "train.py")
        h2 = get_diff_hash(tmpdir, "train.py")
        assert h1 is not None
        assert h1 == h2
        assert len(h1) == 64
