#!/usr/bin/env python3
"""Generate a structured CHANGELOG.md from a project's git history."""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path


CATEGORIES = ("Added", "Fixed", "Changed", "Removed")


def git(*args):
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git command failed")
    return result.stdout


def latest_tag():
    try:
        return git("describe", "--tags", "--abbrev=0").strip()
    except RuntimeError:
        return None


def commit_range(since=None):
    if since:
        return f"{since}..HEAD"
    tag = latest_tag()
    if tag:
        return f"{tag}..HEAD"
    return "HEAD"


def commit_records(revision_range):
    raw = git("log", revision_range, "--pretty=format:%H%x1f%an%x1f%ad%x1f%s%x1e")
    records = []
    for entry in raw.split("\x1e"):
        entry = entry.strip()
        if not entry:
            continue
        parts = entry.split("\x1f")
        if len(parts) != 4:
            continue
        sha, author, date, subject = (p.strip() for p in parts)
        records.append({"sha": sha, "author": author, "date": date, "subject": subject})
    return records


def category_for(subject):
    s = subject.lower()
    # Conventional commit prefixes.
    for prefix in ("feat!", "add!", "fix!", "feat:", "add:"):
        if s.startswith(prefix):
            return "Added"
    if s.startswith(("fix:", "bug:", "patch:")):
        return "Fixed"
    if s.startswith(("change:", "refactor:", "perf:", "cleanup:", "update:", "chore:", "docs:", "style:", "test:")):
        return "Changed"
    if s.startswith(("remove:", "del:", "drop:", "delete:")):
        return "Removed"
    # Fallback keyword detection.
    if any(w in s for w in ("fix", "bug", "patch")):
        return "Fixed"
    if any(w in s for w in ("remove", "delete", "drop")):
        return "Removed"
    if any(w in s for w in ("add", "implement", "introduce", "create")):
        return "Added"
    return "Changed"


def strip_prefix(subject):
    if ":" in subject and len(subject.split(":", 1)[0].replace("!", "").strip().split()) == 1:
        return subject.split(":", 1)[1].strip()
    return subject.strip()


def build_markdown(records, version, date):
    lines = []
    lines.append(f"# Changelog\n")
    lines.append(f"## {version} — {date}\n")
    for cat in CATEGORIES:
        items = [r for r in records if r["category"] == cat]
        if not items:
            continue
        lines.append(f"### {cat}\n")
        for r in items:
            desc = strip_prefix(r["subject"])
            short = r["sha"][:7]
            lines.append(f"- {desc} ({short}) — {r['author']}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main():
    parser = argparse.ArgumentParser(
        description="Generate a CHANGELOG.md from git history"
    )
    parser.add_argument("-o", "--output", default="CHANGELOG.md")
    parser.add_argument("--from", dest="since", default=None, help="commit/tag to start from")
    args = parser.parse_args()

    try:
        records = commit_records(commit_range(args.since))
    except RuntimeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    for r in records:
        r["category"] = category_for(r["subject"])

    version = latest_tag() or "Unreleased"
    date = datetime.now().date().isoformat()
    md = build_markdown(records, version, date)

    out = Path(args.output)
    out.write_text(md, encoding="utf-8")
    print(f"Wrote {out} ({len(records)} commits)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
