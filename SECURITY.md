# Security Policy

## Supported scope

This repository ships `changelog_skill`, a local, standard-library-only CLI that
parses Conventional Commit history and renders Markdown. It has no network
service, no authentication layer, and no runtime credentials.

## Reporting a vulnerability

If you believe you have found a security issue:

1. **Do not open a public issue** with exploit details.
2. Report it privately to the maintainers through GitHub's private vulnerability
   reporting for this repository, or contact the repository owner directly.
3. Include a clear description, impact assessment, affected files/versions, and a
   minimal reproduction or proof of concept.

## Response expectations

- Maintainers will acknowledge receipt as soon as practical.
- Valid reports will be triaged for severity and impact.
- Fixes will be developed and tested before public disclosure details are shared.

## Security design notes

The CLI treats commit text and file inputs as untrusted:

- Git is invoked with fixed argument vectors and `shell=False`.
- Repository, file, and stdin inputs are size-bounded (1 MiB).
- Control characters, Unicode line separators, and bidirectional overrides are
  rejected during parsing.
- Markdown/HTML metacharacters in commit subjects are escaped before rendering.
- Output is written atomically to avoid partial writes.
- CI runs with read-only permissions and includes linting, formatting, tests,
  coverage enforcement, and dependency auditing.

## Secrets and credentials

Never commit `.env` files, API keys, tokens, or runtime logs. See
[.env.example](.env.example) and [.gitignore](.gitignore).
