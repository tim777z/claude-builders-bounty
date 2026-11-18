"""Allow ``python -m changelog_skill`` to invoke the CLI."""

from .cli import main

raise SystemExit(main())
