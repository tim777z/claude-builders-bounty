# Claude Builders Bounty 🤖

> A community bounty board for Claude Code builders.

Building with Claude Code? Have tasks to delegate?
Want to get paid for contributing to AI projects?
You're in the right place.

---

## How it works

**To post a bounty**
1. Open a GitHub issue with a clear description and acceptance criteria
2. Comment `/opire create $XXX` in the issue to set the reward
3. Share the link — contributors will find it

**To claim a bounty**
1. Browse the open issues below
2. Comment `/opire try` in the issue you want to work on
3. Submit a PR — payment is automatic on merge ✅

---

## Active Bounties

| # | Task | Amount | Status |
|---|------|--------|--------|
| [#1](issues/1) | SKILL: Generate a CHANGELOG from git history | $50 | 🟢 Open |
| [#2](issues/2) | TEMPLATE: CLAUDE.md for a Next.js + SQLite project | $75 | 🟢 Open |
| [#3](issues/3) | HOOK: Block destructive bash commands in Claude Code | $100 | 🟢 Open |
| [#4](issues/4) | AGENT: PR reviewer with structured Markdown output | $150 | 🟢 Open |
| [#5](issues/5) | WORKFLOW: n8n + Claude API — automated weekly dev summary | $200 | 🟢 Open |

> Issue numbers above are the board's original references. GitHub has since
> received automation PRs at low numbers, so confirm live status in the
> [Issues](issues) tab before claiming work.

---

## Included tooling

The first bounty deliverable — a **CHANGELOG generator** — is included in this
repository as the dependency-free Python package `changelog_skill`. It parses
Conventional Commits from local git history and renders a release section to
Markdown. See [CHANGELOG.md](CHANGELOG.md) for a real example generated from
this repository.

### Getting started

Requirements: Python 3.10+ and git. No accounts, API keys, databases or
external services are needed.

```bash
git clone https://github.com/tim777z/claude-builders-bounty.git
cd claude-builders-bounty
python -m pip install -e .          # zero runtime dependencies
```

### Usage

```bash
# Generate from the current repository to stdout
python -m changelog_skill --release-version 0.2.0

# Write to a file, reading raw `git log` lines from a file instead of git
python -m changelog_skill --input commits.txt \
  --release-version 0.2.0 --release-date 2026-11-18 --output CHANGELOG.md

# Legacy histories with non-Conventional commits (skipped and counted)
python -m changelog_skill --repo . --skip-invalid --release-version 0.2.0
```

After installation the `changelog-skill` console script is also available.

Exit codes: `0` success, `2` bad CLI usage, `3` invalid input, `4` unreadable
source, `5` unwritable output. CI and scripts can rely on these codes.

### Testing

```bash
python -m unittest discover -s tests -v   # 45 unit and integration tests
python -m ruff check .                     # lint (security rules enabled)
python -m ruff format --check .            # deterministic formatting
```

The same three commands, plus a CLI smoke test, run on every pull request in
[.github/workflows/ci.yml](.github/workflows/ci.yml). Development tooling is
pinned in `requirements-dev.txt`; GitHub Actions are pinned to immutable SHAs.

### Architecture

| Module | Responsibility |
|--------|----------------|
| `changelog_skill/model.py` | Domain types and structured error hierarchy |
| `changelog_skill/parser.py` | Pure, validated parsing of `git log` output |
| `changelog_skill/render.py` | Deterministic Markdown rendering and escaping |
| `changelog_skill/git.py` | Bounded git/filesystem adapters |
| `changelog_skill/cli.py` | Argument parsing, exit codes, atomic output writes |
| `tests/` | Unit tests mirroring each module |

Data flows one way: adapter → parser → renderer → output. Parsing and
rendering are pure functions, so the security-relevant validation is testable
without spawning git or touching the network.

**Security controls:** git is invoked with a fixed argument vector and
`shell=False` (no command injection via `--repo`); repository paths are
resolved and validated; commit count, line count and input size are capped to
prevent resource exhaustion; control characters and unknown commit types are
rejected with line-numbered errors; Markdown/HTML syntax in commit subjects is
escaped so a hostile commit cannot inject active content into a published
CHANGELOG; output is written atomically; CI runs with read-only permissions.

No Docker configuration is provided because the tool has no services or
external infrastructure to orchestrate — adding a container would add attack
surface and maintenance cost without making the project easier to run.

---

## Rules

- Tasks must be related to Claude Code or AI tooling
- Every issue must have clear acceptance criteria before a bounty is activated
- Payment is handled by [Opire](https://opire.dev) (Stripe)
- Quality over speed — a solid PR beats a fast one
- Send implementation and its tests in the same focused commit; use
  Conventional Commit messages (`feat:`, `fix:`, `test:`, `docs:`, `ci:`)
- Never commit credentials, `.env` files or runtime logs (see
  [.env.example](.env.example) and `.gitignore`)

---

## Community

- 🐦 X: [@ClaudeBounty](https://x.com/ClaudeBounty)
- 📧 Contact: claudebounty@gmail.com

---

*Started by the Claude builder community · March 2026 · MIT License*
