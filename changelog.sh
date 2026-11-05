#!/usr/bin/env bash
# Generate a CHANGELOG from this repository's git history.
# Accepted stack: Python 3 (used); output defaults to ./CHANGELOG.md
if command -v python3 >/dev/null 2>&1; then PY=python3
elif command -v python >/dev/null 2>&1; then PY=python
else
  echo "python 3 is required" >&2
  exit 1
fi
cd "$(git rev-parse --show-toplevel)"
"$PY" scripts/generate_changelog.py "$@"