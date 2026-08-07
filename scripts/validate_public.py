#!/usr/bin/env python3
"""Validate repository structure and common public-release hygiene issues."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
REQUIRED_FILES = [
    ROOT / "README.md",
    ROOT / "README.zh-CN.md",
    ROOT / "LICENSE",
    ROOT / "SECURITY.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / "skills/watch/SKILL.md",
    ROOT / "skills/watch/agents/openai.yaml",
    ROOT / "skills/watch/scripts/check_dependencies.sh",
    ROOT / "skills/watch/scripts/prepare_video.sh",
    ROOT / "skills/watch/scripts/scene_index.py",
    ROOT / "tests/test_scene_index.py",
]
TEXT_SUFFIXES = {
    "",
    ".md",
    ".py",
    ".sh",
    ".yaml",
    ".yml",
    ".txt",
    ".json",
    ".toml",
}
FORBIDDEN_PATTERNS = {
    "macOS personal home path": re.compile(r"/Users/[A-Za-z0-9._-]+/"),
    "Linux personal home path": re.compile(r"/home/[A-Za-z0-9._-]+/"),
    "Windows personal home path": re.compile(
        r"[A-Za-z]:\\\\Users\\\\[^\\\\\s]+\\\\"
    ),
    "email address": re.compile(
        r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE
    ),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "GitHub classic token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    "GitHub fine-grained token": re.compile(r"\bgithub_pat_[A-Za-z0-9_]{30,}\b"),
    "OpenAI-style secret": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "AWS access key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "credential-bearing URL": re.compile(
        r"https?://[^/\s:@]+:[^/\s@]+@", re.IGNORECASE
    ),
}


def iter_text_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if ".git" in path.parts or not path.is_file():
            continue
        if path.suffix.lower() in TEXT_SUFFIXES:
            files.append(path)
    return files


def check_required_files(errors: list[str]) -> None:
    for path in REQUIRED_FILES:
        if not path.is_file():
            errors.append(f"missing required file: {path.relative_to(ROOT)}")


def check_skill_frontmatter(errors: list[str]) -> None:
    path = ROOT / "skills/watch/SKILL.md"
    if not path.is_file():
        return
    content = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---\n", content, re.DOTALL)
    if not match:
        errors.append("skills/watch/SKILL.md has invalid frontmatter")
        return
    frontmatter = match.group(1)
    keys = [
        line.split(":", 1)[0]
        for line in frontmatter.splitlines()
        if line and not line[0].isspace() and ":" in line
    ]
    if keys[:2] != ["name", "description"]:
        errors.append("SKILL.md frontmatter must start with name and description")
    allowed_keys = {
        "name",
        "description",
        "version",
        "type",
        "risk_level",
        "status",
        "disable-model-invocation",
        "tags",
        "requires",
        "metadata",
        "market",
    }
    unknown_keys = sorted(set(keys) - allowed_keys)
    if unknown_keys:
        errors.append(f"SKILL.md frontmatter has unsupported top-level keys: {', '.join(unknown_keys)}")
    if not re.search(r"^name:\s*watch\s*$", frontmatter, re.MULTILINE):
        errors.append("SKILL.md name must be watch")
    if "[TODO" in content:
        errors.append("SKILL.md contains an unresolved TODO")
    if len(content.splitlines()) > 500:
        errors.append("SKILL.md exceeds 500 lines")


def check_interface(errors: list[str]) -> None:
    path = ROOT / "skills/watch/agents/openai.yaml"
    if not path.is_file():
        return
    content = path.read_text(encoding="utf-8")
    if "$watch" not in content:
        errors.append("agents/openai.yaml default_prompt must mention $watch")


def check_hygiene(errors: list[str]) -> None:
    for path in iter_text_files():
        content = path.read_text(encoding="utf-8", errors="replace")
        relative = path.relative_to(ROOT)
        for label, pattern in FORBIDDEN_PATTERNS.items():
            if pattern.search(content):
                errors.append(f"{relative}: contains {label}")


def check_shell_syntax(errors: list[str]) -> None:
    for path in ROOT.rglob("*.sh"):
        result = subprocess.run(
            ["bash", "-n", str(path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode:
            errors.append(f"{path.relative_to(ROOT)}: {result.stderr.strip()}")


def check_video_scope_guard(errors: list[str]) -> None:
    path = ROOT / "skills/watch/scripts/prepare_video.sh"
    if not path.is_file():
        return
    content = path.read_text(encoding="utf-8")
    if content.count("--no-playlist") < 2:
        errors.append("prepare_video.sh must pass --no-playlist to every yt-dlp invocation")


def check_symlinks(errors: list[str]) -> None:
    for path in ROOT.rglob("*"):
        if ".git" not in path.parts and path.is_symlink():
            errors.append(f"symlinks are not allowed: {path.relative_to(ROOT)}")


def main() -> int:
    errors: list[str] = []
    check_required_files(errors)
    check_skill_frontmatter(errors)
    check_interface(errors)
    check_hygiene(errors)
    check_shell_syntax(errors)
    check_video_scope_guard(errors)
    check_symlinks(errors)

    if errors:
        print("Public validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("Public validation passed.")
    print(f"Checked {len(iter_text_files())} text files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
