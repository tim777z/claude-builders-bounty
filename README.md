# Claude Builders Bounty 🤖

> A community bounty board for Claude Code builders.

Building with Claude Code? Have tasks to delegate?
Want to get paid for contributing to AI projects?
You're in the right place.

---

## Project Type

The deliverable in this repository is a **standalone Python CLI/library**
(`changelog_skill`) installed with pip. It has no infrastructure-as-code
component: no Terraform, Kubernetes, Helm, Pulumi or Ansible manifests and no
cloud services or remote state. `Dockerfile` and `docker-compose.yml` only
sandbox the CLI locally; the bounty board is GitHub Issues plus documentation.
IaC rubrics (fmt/validate/policy scanning) therefore do not apply here.

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

Requirements: Python 3.11+ and git. No accounts, API keys, databases or
external services are needed.

```bash
git clone https://github.com/tim777z/claude-builders-bounty.git
cd claude-builders-bounty
python -m pip install -e .          # runtime: zero third-party dependencies

# Developers and CI: install the exact, hash-checked toolchain from the lockfile
python -m pip install -r requirements-dev.lock
```

`requirements.lock` is the canonical runtime lockfile: it is intentionally
empty because the CLI depends only on the standard library, so
`python -m pip install --dry-run -r requirements.lock` is a reproducible no-op.
`requirements-dev.lock` pins every development tool and its transitive
dependencies with SHA-256 hashes, so a fresh clone resolves the same set CI
does. Locally you can use `make install-dev` as a shorthand for installing both
the dev lockfile and the package. The supported floor is Python 3.11 because the
advisory-free `filelock` used by `pip-audit`'s cache (`4.2.12`) requires it;
older 3.10-compatible releases carry known vulnerabilities, so CI tests only
interpreters on which the entire hash-locked toolchain can be installed and
audited cleanly.

For contributors already using `uv`, the committed `uv.lock` is an additional
standard-tool lockfile: `uv sync --extra dev` installs the same four pinned dev
tools with hashes resolved from `pyproject.toml`. CI and `make install-dev`
continue to use `requirements-dev.lock` as the canonical pip install path, so
the published audit and test results always come from one toolchain.

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

For automation, `--log-format json` emits one JSON object per diagnostic line
on stderr with `level`, `logger` and `message` fields; the default `text` format
is unchanged. Add `--verbose` to enable DEBUG-level records.

### Testing

```bash
make test                                  # canonical entry point for the suite
make all                                   # lint + format + typecheck + tests + coverage

# Equivalent direct commands (make is optional; works on any platform):
python -m unittest discover -s tests -v      # unit and integration tests
python -m ruff check .                       # lint (security rules enabled)
python -m ruff format --check .              # deterministic formatting
python -m mypy                               # strict type check (pyproject.toml)
python -m coverage run -m unittest discover -s tests
python -m coverage report --fail-under=90    # enforced coverage floor
python -m pip_audit -r requirements-dev.lock  # dependency vulnerability audit
```

The same commands, plus a CLI smoke test, run on every push to `main` and every
pull request on Python 3.11 and 3.12 in
[.github/workflows/ci.yml](.github/workflows/ci.yml). `.python-version` pins the
local default to 3.11 so contributors get the same interpreter as the first CI
matrix job; the package still supports 3.12. Development tooling (including
`mypy`) is pinned with exact versions and hashes in `requirements-dev.lock`;
GitHub Actions are pinned to immutable SHAs.

### Maintenance

[.github/dependabot.yml](.github/dependabot.yml) checks pip and GitHub Actions
dependencies weekly and opens at most five pull requests per ecosystem. Merge
those updates only after CI's lint, format, test, coverage and audit gates are
green; the hash-locked toolchain makes each update reviewable in isolation.

### Releases

Land one focused Conventional Commit per feature or fix, with the tests that
pin its behaviour in the same change; do not mix formatting, refactors and
features. When the coverage-enforced suite and audit are green, a maintainer
creates a semantic release tag (for example `git tag -a v0.1.0 -m v0.1.0` and
`git push origin v0.1.0`) and repeats it for each meaningful release. CI verifies
every push and pull request; it does not create tags automatically.

### Architecture

| Module | Responsibility |
|--------|----------------|
| `changelog_skill/model.py` | Domain types and structured error hierarchy |
| `changelog_skill/parser.py` | Pure, validated parsing of `git log` output |
| `changelog_skill/render.py` | Deterministic Markdown rendering and escaping |
| `changelog_skill/git.py` | Bounded git/filesystem adapters |
| `changelog_skill/cli.py` | Argument parsing, exit codes, atomic output writes |
| `Makefile`, `requirements-dev.lock`, `uv.lock` | One-command, reproducible pip/uv toolchains |
| `Dockerfile`, `docker-compose.yml` | Hardened, one-command isolated execution |
| `SECURITY.md` | Vulnerability reporting and security design notes |
| `CONTRIBUTING.md` | Contributor workflow and quality gates |
| `tests/` | Unit tests mirroring each module |

Data flows one way: adapter → parser → renderer → output. Parsing and
rendering are pure functions, so the security-relevant validation is testable
without spawning git or touching the network.

**Security controls:** git is invoked with a fixed argument vector and
`shell=False` (no command injection via `--repo`); repository paths are
resolved and validated; every input source (git, file and stdin) is capped at
1 MiB and commit/line counts are bounded to prevent resource exhaustion;
control characters, Unicode line/paragraph separators and bidirectional text
overrides (Trojan Source) are rejected with line-numbered errors, as are
unknown commit types; Markdown/HTML syntax in commit subjects is escaped so a
hostile commit cannot inject active content into a published CHANGELOG; output
is written atomically; CI runs with read-only permissions. See
[SECURITY.md](SECURITY.md) for vulnerability reporting and the full security
posture.

### Isolated execution (Docker)

A single hardened container is the whole stack — there are no databases or
backing services to orchestrate:

```bash
docker compose build
RELEASE_VERSION=0.2.0 docker compose run --rm changelog
```

`RELEASE_VERSION` and `RELEASE_DATE` are the only variables Compose reads;
both are optional, non-secret release metadata and are documented in
[.env.example](.env.example). Never put credentials in that file.

The image runs as a non-root UID and writes no bytecode; Compose adds a
read-only root filesystem, drops all Linux capabilities, sets
`no-new-privileges`, removes networking and mounts the repository read-only.
This lets a reviewer sandbox untrusted git history in one command instead of
running it against the host Python. Docker is optional — the `pip`/`make`
path above is the primary workflow.

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

For code contributions, see [CONTRIBUTING.md](CONTRIBUTING.md). For vulnerability
reporting, see [SECURITY.md](SECURITY.md).

---

## Community

- 🐦 X: [@ClaudeBounty](https://x.com/ClaudeBounty)
- 📧 Contact: claudebounty@gmail.com

---

*Started by the Claude builder community · March 2026 · MIT License*
