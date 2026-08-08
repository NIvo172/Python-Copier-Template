# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///

"""Initialise Git, dependencies, generated state, and the initial project version."""

from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GIT_NAME = "John Doe"
DEFAULT_GIT_EMAIL = "john.doe@example.com"
DEFAULT_TAG = "v0.0.1"


@dataclass(frozen=True)
class InitOptions:
    """Configuration for the generated-project initialization workflow."""

    git_name: str
    git_email: str
    tag: str


def write(message: str) -> None:
    """Write a message to the terminal."""
    print(message, flush=True)


def command_environment() -> dict[str, str]:
    """Return a subprocess environment without a foreign active virtual environment."""
    environment = os.environ.copy()
    active_environment = environment.get("VIRTUAL_ENV")
    project_environment = PROJECT_ROOT / ".venv"
    if active_environment is not None and Path(active_environment).resolve() != project_environment.resolve():
        environment.pop("VIRTUAL_ENV", None)
    return environment


def stream(command: list[str]) -> int:
    """Run a command with terminal output and return its exit status."""
    write(f"$ {shlex.join(command)}")
    return subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        check=False,
        env=command_environment(),
    ).returncode


def run(command: list[str]) -> None:
    """Run a command and raise when it exits unsuccessfully."""
    return_code = stream(command)
    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, command)


def worktree_fingerprint() -> bytes:
    """Return a content-sensitive fingerprint of non-ignored repository changes."""
    tracked_changes = subprocess.run(
        ["git", "diff", "--binary", "HEAD"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        check=True,
    ).stdout
    untracked_result = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        check=True,
    )

    parts = [tracked_changes, b"\0untracked\0", untracked_result.stdout]
    for raw_path in untracked_result.stdout.split(b"\0"):
        if not raw_path:
            continue
        path = PROJECT_ROOT / os.fsdecode(raw_path)
        parts.append(raw_path)
        if path.is_symlink():
            parts.append(str(path.readlink()).encode(errors="surrogateescape"))
        elif path.is_file():
            parts.append(path.read_bytes())

    return b"".join(parts)


def run_precommit_until_clean(max_attempts: int = 3) -> None:
    """Run all hooks repeatedly while automatic fixes keep changing files."""
    if not (PROJECT_ROOT / ".pre-commit-config.yaml").is_file():
        return

    command = ["uv", "run", "pre-commit", "run", "--all-files", "--show-diff-on-failure"]
    for attempt in range(1, max_attempts + 1):
        state_before = worktree_fingerprint()
        return_code = stream(command)
        if return_code == 0:
            return
        if worktree_fingerprint() == state_before:
            write("Pre-commit failed without modifying files; not retrying.")
            raise subprocess.CalledProcessError(return_code, command)
        if attempt < max_attempts:
            write(f"Pre-commit attempt {attempt} modified files; retrying.")

    raise subprocess.CalledProcessError(return_code, command)


def has_git_head() -> bool:
    """Return whether the repository already has at least one commit."""
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "HEAD"],
        cwd=PROJECT_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode not in {0, 128}:
        write(f"git rev-parse returned unexpected status {result.returncode}.")
    return result.returncode == 0


def has_staged_changes() -> bool:
    """Return whether the Git index differs from HEAD."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=PROJECT_ROOT,
        check=False,
    )
    return result.returncode == 1


def ensure_clean_worktree() -> None:
    """Fail when initialization leaves non-ignored repository changes."""
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    if result.stdout.strip():
        raise RuntimeError(f"Project initialization left repository changes:\n{result.stdout.rstrip()}")


def ensure_tag(tag: str) -> None:
    """Create the release tag, or verify an existing tag points at HEAD."""
    tag_result = subprocess.run(
        ["git", "rev-parse", "--verify", f"refs/tags/{tag}"],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    if tag_result.returncode != 0:
        run(["git", "tag", tag])
        return

    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=PROJECT_ROOT,
        stdout=subprocess.PIPE,
        text=True,
        check=True,
    ).stdout.strip()
    if tag_result.stdout.strip() != head:
        raise RuntimeError(f"Tag {tag!r} already exists and does not point at HEAD.")
    write(f"Tag {tag} already exists at HEAD; leaving it unchanged.")


def has_dvc_stages() -> bool:
    """Return whether dvc.yaml declares at least one pipeline stage."""
    dvc_file = PROJECT_ROOT / "dvc.yaml"
    if not dvc_file.is_file():
        return False

    lines = dvc_file.read_text(encoding="utf-8").splitlines()
    for index, line in enumerate(lines):
        if line.strip() != "stages:":
            continue
        base_indent = len(line) - len(line.lstrip())
        for candidate in lines[index + 1 :]:
            stripped = candidate.strip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = len(candidate) - len(candidate.lstrip())
            if indent <= base_indent:
                return False
            return stripped != "{}"
        return False

    return "stages: {}" not in dvc_file.read_text(encoding="utf-8")


def require_commands() -> None:
    """Fail early when required executables are unavailable."""
    missing = [command for command in ("git", "uv") if shutil.which(command) is None]
    if missing:
        joined = ", ".join(missing)
        raise RuntimeError(f"Required command(s) not found on PATH: {joined}")


def parse_args() -> InitOptions:
    """Parse initialization options."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--git-name", default=DEFAULT_GIT_NAME, help="Repository-local Git author name.")
    parser.add_argument("--git-email", default=DEFAULT_GIT_EMAIL, help="Repository-local Git author email.")
    parser.add_argument("--tag", default=DEFAULT_TAG, help="Initial release tag.")
    namespace = parser.parse_args()
    return InitOptions(
        git_name=str(namespace.git_name),
        git_email=str(namespace.git_email),
        tag=str(namespace.tag),
    )


def initialize_project(args: InitOptions) -> None:
    """Initialise Git, resolve dependencies, and commit generated state."""
    require_commands()

    run(["git", "init", "--initial-branch=main"])
    run(["git", "config", "--local", "user.name", args.git_name])
    run(["git", "config", "--local", "user.email", args.git_email])

    if not has_git_head():
        run(["git", "add", "."])
        run(["git", "commit", "-m", "Initial project"])
    else:
        write("Git already has a commit; skipping the initial commit.")

    run(["uv", "sync"])
    run_precommit_until_clean()

    if has_dvc_stages():
        run(["uv", "run", "dvc", "repro"])
        run_precommit_until_clean()

    run(["git", "add", "."])
    if has_staged_changes():
        run(["git", "commit", "-m", "Lock dependencies and generated project state"])
    else:
        write("No dependency or generated-state changes require a second commit.")

    run(["uv", "sync"])
    ensure_clean_worktree()


def finalize_initial_version(tag: str) -> None:
    """Create the initial version tag and resynchronise the installed package."""
    ensure_clean_worktree()
    ensure_tag(tag)
    run(["uv", "sync"])
    ensure_clean_worktree()


def main() -> int:
    """Run the generated-project initialization workflow."""
    args = parse_args()

    try:
        write(f"Project root: {PROJECT_ROOT}")
        initialize_project(args)
        finalize_initial_version(args.tag)
        write("Project initialization completed successfully.")
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"Project initialization failed: {error}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
