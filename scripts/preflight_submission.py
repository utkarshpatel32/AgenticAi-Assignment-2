"""Pre-publish checks for the Assignment 2 GitHub repository.

This is a guardrail, not a complete secret scanner. Always review `git status`
and `git diff --cached` before pushing.
"""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "README.md", "VIDEO_WALKTHROUGH.md", "GITHUB_SUBMISSION.md",
    "SUBMISSION_CHECKLIST.md", "server.js", "bridge.py", "package.json",
    ".env.example", ".gitignore", "agent.py", "agent_assignment1_baseline.py",
    "database.py", "security.py", "tools/student_tools.py",
    "retrieval/policy_search.py", "data/sample_students.csv",
    "data/sample_college_policy.md", "evaluation/runner.py",
    "evaluation/ASSIGNMENT2_EVALUATION_REPORT.md", "evaluation/test_questions.json",
    "tests/test_assignment2.py", "tests/test_assignment1.py",
    "scripts/setup_demo_accounts.py", "scripts/run_evaluation.py",
]
TEXT_SUFFIXES = {".py", ".js", ".json", ".md", ".txt", ".csv", ".html", ".css", ".yml", ".yaml", ".toml"}
SECRET_PATTERNS = {
    "Groq API key": re.compile(r"\bgsk_[A-Za-z0-9]{20,}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "private-key block": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "common baked-in demo password": re.compile(r"(?:Student|Approver)@123", re.IGNORECASE),
}
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache"}
SKIP_NAMES = {".env", "bridge_errors.log"}


def tracked_files() -> list[Path] | None:
    if not (ROOT / ".git").exists():
        return None
    try:
        output = subprocess.run(
            ["git", "ls-files", "-z"], cwd=ROOT, check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        ).stdout
        return [ROOT / part.decode("utf-8", errors="replace") for part in output.split(b"\0") if part]
    except (OSError, subprocess.CalledProcessError):
        return None


def main() -> int:
    errors: list[str] = []
    notes: list[str] = []
    for relative in REQUIRED:
        if not (ROOT / relative).is_file():
            errors.append(f"Missing required file: {relative}")

    ignore_path = ROOT / ".gitignore"
    ignore_text = ignore_path.read_text(encoding="utf-8", errors="replace") if ignore_path.exists() else ""
    for rule in (".env", "*.db", "*.sqlite", "*.sqlite3", ".venv/"):
        if rule not in ignore_text:
            errors.append(f".gitignore should include rule: {rule}")

    tracked = tracked_files()
    if tracked is not None:
        for path in tracked:
            if path.name == ".env" or (path.name.startswith(".env.") and path.name != ".env.example"):
                errors.append(f"Secret environment file is Git-tracked: {path.relative_to(ROOT).as_posix()}")
            if path.suffix.lower() in {".db", ".sqlite", ".sqlite3"} or path.name.endswith((".db-wal", ".db-shm", ".sqlite-wal", ".sqlite-shm")):
                errors.append(f"Local database file is Git-tracked: {path.relative_to(ROOT).as_posix()}")
        candidates = [p for p in tracked if p.is_file()]
    else:
        notes.append("Git repository not initialized; tracked-file checks run after `git init`.")
        candidates = []
        for path in ROOT.rglob("*"):
            if path.is_file() and not any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
                if path.name not in SKIP_NAMES and path.suffix.lower() in TEXT_SUFFIXES:
                    candidates.append(path)

    for path in candidates:
        if path.name in SKIP_NAMES or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            notes.append(f"Could not scan {path}: {exc}")
            continue
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(content):
                errors.append(f"Possible {label} found in {path.relative_to(ROOT).as_posix()}.")

    env_path = ROOT / ".env"
    if env_path.exists():
        notes.append("A local .env exists; confirm it is untracked and contains only local settings.")

    if errors:
        print("ASSIGNMENT 2 PREFLIGHT: FAILED")
        for item in errors:
            print(f" - ERROR: {item}")
        for item in notes:
            print(f" - NOTE: {item}")
        return 1

    print("ASSIGNMENT 2 PREFLIGHT: PASS")
    print(f"Checked {len(REQUIRED)} required files and scanned text files for common secret patterns.")
    print("This is not a full secret scanner. Review git status and git diff --cached before pushing.")
    for item in notes:
        print(f" - NOTE: {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
