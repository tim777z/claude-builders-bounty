---
name: changelog-generator
description: Generate a structured CHANGELOG.md from git history since the last tag.
triggers:
  - /generate-changelog
---

# SKILL: generate-changelog

When the user asks to generate a changelog:

1. Determine the repository root (run from any subdir).
2. Find the latest tag if one exists; otherwise generate from the entire history.
3. Run `python3 scripts/generate_changelog.py --output CHANGELOG.md`.
4. Auto-categorize commits into **Added**, **Fixed**, **Changed**, **Removed** based on conventional commit prefixes.
5. Write the output to `CHANGELOG.md` next to the README.

Acceptance criteria covered:
- Works via `/generate-changelog` or `bash changelog.sh`
- Fetches commits since last tag
- Categorizes into Added / Fixed / Changed / Removed
- Outputs formatted `CHANGELOG.md`
- Deterministic Markdown output
- Three-step setup in README below
