# r2x-core automation tasks.

set dotenv-load := false

default:
    @just --list

# Install dev dependencies.
sync:
    uv sync --all-groups --upgrade

# Update uv.lock.
lock:
    uv lock

# Install git hooks.
hooks-install:
    uv run prek install

# Format code.
format *ARGS:
    uv run ruff format {{ARGS}}

# Lint code.
lint *ARGS:
    uv run ruff check --config=pyproject.toml {{ARGS}}

# Type check.
type:
    uv run ty check src/

# Run tests.
test *ARGS:
    uv run pytest -q --cov-report=term-missing:skip-covered {{ARGS}}

# Build documentation.
docs:
    uv run sphinx-build -M html docs/source docs/build

# Run prek hooks (format, lint, type check, file hygiene).
hooks:
    uv run prek run --all-files

# Comprehensive verification: hooks + tests with strict coverage.
verify: hooks
    uv run pytest --tb=short --cov --cov-report=term-missing:skip-covered
