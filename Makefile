# Single entry point for local development and CI.
# CI invokes these same targets from .github/workflows/ci.yml so a green local
# `make all` means a green pull request.
.PHONY: all install-dev lint format-check format typecheck test coverage audit clean

PYTHON ?= python

all: lint format-check typecheck test coverage

install-dev:
	$(PYTHON) -m pip install --disable-pip-version-check -r requirements-dev.lock
	$(PYTHON) -m pip install --disable-pip-version-check -e .

lint:
	$(PYTHON) -m ruff check .

format-check:
	$(PYTHON) -m ruff format --check .

format:
	$(PYTHON) -m ruff format .

typecheck:
	$(PYTHON) -m mypy

test:
	$(PYTHON) -m unittest discover -s tests -v

coverage:
	$(PYTHON) -m coverage run -m unittest discover -s tests
	$(PYTHON) -m coverage report --fail-under=90

audit:
	$(PYTHON) -m pip_audit -r requirements-dev.lock

clean:
	$(PYTHON) -m coverage erase
