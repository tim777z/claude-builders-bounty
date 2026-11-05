# Claude Builders Bounty - CHANGELOG generator (issue #1)

A small utility that generates `CHANGELOG.md` from a project's git history and
auto-categorizes commits into Added / Fixed / Changed / Removed.

## Setup (3 steps)
1. Clone this repository and open it in Claude Code.
2. Run: `bash changelog.sh` (or `python3 scripts/generate_changelog.py`).
3. Open `CHANGELOG.md` for the structured output.

## Sample output
See `samples/changelog.sample.md`.

## How to test on a real repository
```bash
git clone <any-repo>
cd <any-repo>
python3 .../scripts/generate_changelog.py -o /tmp/changelog.md
cat /tmp/changelog.md
```
