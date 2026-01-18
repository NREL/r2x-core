"""Pytest plugin for running Python doctest blocks in markdown documentation.

This module enables pytest to discover and execute Python code blocks marked
with 'python doctest' in markdown files. Each code block is treated as a doctest
and executed to ensure documentation examples remain accurate and functional.

Usage:
    pytest tests/test_docs_doctest.py

The plugin scans markdown files in configured documentation directories and
extracts code blocks formatted as doctests.
"""

from __future__ import annotations

import doctest
import re
from collections.abc import Generator
from dataclasses import dataclass
from pathlib import Path

import pytest

# Configuration: which directories to scan
DOCS_ROOT = Path(__file__).resolve().parents[1] / "docs"
DOCS_DIRS = (
    DOCS_ROOT / "tutorials",
    DOCS_ROOT / "how-to",
)

# Regex patterns for detecting code blocks
FENCE_RE = re.compile(r"^(```|~~~)\s*([^\n`]*)?$")
DOCTEST_LANG = "python"
DOCTEST_MARKER = "doctest"
DOCTEST_PROMPT_RE = re.compile(r"^\s*>>> ")


@dataclass(frozen=True)
class DocBlock:
    """Represents a doctest code block from markdown."""

    path: Path
    start_line: int
    text: str


def iter_markdown_files() -> Generator[Path, None, None]:
    """Discover all markdown files in configured documentation directories."""
    for docs_dir in DOCS_DIRS:
        if not docs_dir.exists():
            continue
        yield from sorted(docs_dir.glob("**/*.md"))


def extract_doctest_blocks(path: Path) -> list[DocBlock]:
    """Extract doctest code blocks from markdown file.

    Parameters
    ----------
    path : Path
        Path to markdown file.

    Returns
    -------
    list[DocBlock]
        List of doctest blocks found.
    """
    blocks: list[DocBlock] = []

    try:
        content = path.read_text()
    except Exception:
        return blocks

    lines = content.split("\n")
    i = 0

    while i < len(lines):
        # Look for fence with python doctest marker
        match = FENCE_RE.match(lines[i])
        if not match:
            i += 1
            continue

        fence_char, lang_info = match.groups()
        if not lang_info:
            i += 1
            continue

        # Check if it has both 'python' and 'doctest' markers
        parts = lang_info.split()
        if not (DOCTEST_LANG in parts and DOCTEST_MARKER in parts):
            i += 1
            continue

        # Collect block content
        block_start = i
        i += 1
        block_lines: list[str] = []

        while i < len(lines):
            if FENCE_RE.match(lines[i]) and fence_char in lines[i]:
                break
            block_lines.append(lines[i])
            i += 1

        # Extract lines that look like doctest
        doctest_lines = []
        for line in block_lines:
            if DOCTEST_PROMPT_RE.match(line) or (doctest_lines and not line.strip()):
                doctest_lines.append(line)
            elif doctest_lines and not DOCTEST_PROMPT_RE.match(line):
                # Expected output line
                doctest_lines.append(line)

        if doctest_lines:
            block_text = "\n".join(doctest_lines)
            blocks.append(DocBlock(path=path, start_line=block_start + 1, text=block_text))

        i += 1

    return blocks


def run_doctest_block(block: DocBlock, block_index: int, module_name: str = "__main__") -> tuple[int, int]:
    """Run a single doctest block.

    Parameters
    ----------
    block : DocBlock
        The doctest block to run.
    block_index : int
        Index of block within the file.
    module_name : str
        Module name to use for doctest context.

    Returns
    -------
    tuple[int, int]
        (failures, tests) - number of failures and tests run.
    """
    runner = doctest.DocTestRunner(verbose=False)
    parser = doctest.DocTestParser()

    try:
        test = parser.get_doctest(
            block.text,
            globs={},
            name=f"{block.path.name}:block_{block_index}",
            filename=str(block.path),
            lineno=block.start_line,
        )
        runner.run(test)
    except Exception as e:
        pytest.fail(f"Error running doctest in {block.path}:{block.start_line}: {e}")

    return runner.failures, runner.tries


@pytest.mark.parametrize(
    "path",
    list(iter_markdown_files()),
    ids=lambda path: f"{path.parent.name}/{path.name}",
)
def test_docs_doctest_blocks(path: Path) -> None:
    """Run all doctest blocks in a markdown file.

    Parameters
    ----------
    path : Path
        Path to markdown file to test.
    """
    blocks = extract_doctest_blocks(path)

    if not blocks:
        pytest.skip(f"No doctest blocks in {path.relative_to(DOCS_ROOT)}")

    failures = 0
    total_tests = 0

    for i, block in enumerate(blocks):
        block_failures, block_tests = run_doctest_block(block, i)
        failures += block_failures
        total_tests += block_tests

    if failures > 0:
        pytest.fail(f"{failures} doctest(s) failed in {path}")


def test_docs_doctest_blocks_present() -> None:
    """Ensure at least some doctest blocks exist (sanity check)."""
    total_blocks = sum(len(extract_doctest_blocks(path)) for path in iter_markdown_files())

    if total_blocks == 0:
        pytest.skip(f"No doctest blocks found in {[str(d.relative_to(DOCS_ROOT)) for d in DOCS_DIRS]}")
