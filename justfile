# r2x-core automation tasks.

set dotenv-load := false

# List available recipes.
default:
    @just --list

# Install dev dependencies.
sync:
    uv sync --dev

# Update uv.lock.
lock:
    uv lock

# Install all git hooks (prek, commit-msg, pre-push).
hooks-install:
    uv run prek install

# Run prek stage hooks on all files.
hooks:
    uv run prek run --all-files

# Run pre-push stage hooks (includes the quick pytest hook).
hooks-push:
    uv run prek run --all-files --hook-stage pre-push

# Run the commit-msg hook with a sample message.
hooks-commit-msg MESSAGE="chore: check commit-msg hook":
    tmp="$(mktemp)"
    printf '%s\n' "{{MESSAGE}}" > "$tmp"
    uv run prek run commitizen --hook-stage commit-msg --commit-msg-filename "$tmp"
    rm -f "$tmp"

# Run all hook stages.
hooks-all: hooks hooks-push hooks-commit-msg

# Formatting and linting.
format *ARGS:
    uv run ruff format {{ARGS}}

format-check *ARGS:
    uv run ruff format --check {{ARGS}}

lint *ARGS:
    uv run ruff check --config=pyproject.toml {{ARGS}}

lint-fix *ARGS:
    uv run ruff check --fix --config=pyproject.toml {{ARGS}}

# Type checking.
typecheck:
    uv run ty check src/
    uv run mypy --config-file=pyproject.toml src/

typecheck-ty:
    uv run ty check src/

typecheck-mypy:
    uv run mypy --config-file=pyproject.toml src/

# Tests.
test *ARGS:
    uv run pytest {{ARGS}}

test-fast:
    uv run pytest -q -m "not slow" --maxfail=1 --disable-warnings

test-cov:
    uv run pytest --cov --cov-report=xml

# Documentation.
docs:
    uv run sphinx-build -M html docs/source docs/build

# Full local verification.
check: hooks-all typecheck test
