# Contributing

Thanks for contributing to `claude-builders-bounty`. This repository ships a small, security-sensitive Python CLI (`changelog_skill`) and a bounty-board README. Changes should be small, reviewable, and paired with tests.

## Development setup

Requirements: Python 3.11+ and Git. The runtime CLI has zero third-party dependencies.

```bash
git clone https://github.com/tim777z/claude-builders-bounty.git
cd claude-builders-bounty
python -m pip install -r requirements-dev.lock
python -m pip install -e .
```

`requirements-dev.lock` is the canonical, hash-pinned pip toolchain. `uv.lock` is also committed for contributors who prefer `uv sync --extra dev`; CI and release verification use the pip lockfile.

## Local verification

Run the same checks CI enforces before opening a PR:

```bash
make all
# or, without make:
python -m ruff check .
python -m ruff format --check .
python -m mypy
python -m coverage run -m unittest discover -s tests
python -m coverage report --fail-under=90
python -m pip_audit -r requirements-dev.lock
```

## Change discipline

- **One focused change per commit/PR.** Do not mix formatting, refactors, features, and dependency bumps.
- **Tests in the same change.** Add or update tests that pin the behavior you changed. Do not weaken tests just to pass.
- **Conventional Commits.** Use `feat:`, `fix:`, `test:`, `docs:`, `ci:`, `build:`, `chore:` etc., with an optional scope, e.g. `fix(parser): reject oversized commit lines`.
- **Security first.** Treat commit messages, files, stdin, and git output as untrusted input. Preserve bounds, validation, escaping, and `shell=False` subprocess boundaries.
- **No secrets.** Never commit `.env` files, credentials, tokens, private keys, or runtime logs. See [.env.example](.env.example) and [SECURITY.md](SECURITY.md).

## Pull requests

- Include a clear problem statement, acceptance criteria, and verification commands/results.
- Keep public APIs typed; the package ships `py.typed` and strict mypy is enforced.
- For dependency updates, prefer Dependabot PRs and merge only when lint, format, typecheck, tests, coverage, and audit are green.
- For security issues, follow [SECURITY.md](SECURITY.md) instead of opening a public exploit report.
