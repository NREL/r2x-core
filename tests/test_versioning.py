"""Tests for the versioning comparsing."""

import pytest

from r2x_core.versioning import GitVersioningStrategy, SemanticVersioningStrategy


@pytest.mark.parametrize(
    "current,target,expected",
    [
        ("1.0.0", "2.0.0", -1),
        ("1.1.0", "1.0.0", 1),
        ("1.0.1", "1.0.0", 1),
        ("1.0.0", "1.0.0", 0),
        ("1.0", "1.1", -1),
        ("2", "1", 1),
        ("1.0.0", "1.0", 0),
        ("1.10.0", "1.9.0", 1),
        ("1.0.10", "1.0.9", 1),
        ("0.0.1", "0.1.0", -1),
        ("10.0.0", "9.9.9", 1),
        ("1.2.3", "1.2.4", -1),
        ("1.2.3", "1.3.0", -1),
        ("1.2.3", "2.0.0", -1),
    ],
    ids=[
        "major_upgrade",
        "minor_downgrade",
        "patch_upgrade",
        "equal_versions",
        "two_components",
        "single_component",
        "mixed_3v2_components",
        "double_digit_minor",
        "double_digit_patch",
        "pre_1_0_versions",
        "cross_decade_boundary",
        "patch_update",
        "minor_update",
        "major_update",
    ],
)
def test_semantic_versioning_strategy_compare_less(current, target, expected):
    """Test version comparison: current < target."""
    strategy = SemanticVersioningStrategy()
    assert strategy.compare_versions(current, target) == expected


@pytest.mark.parametrize(
    "current,target,expected",
    [
        ("abc123", "def456", -1),
        ("def456", "abc123", 1),
        ("abc123", "abc123", 0),
        ("abc123", "ghi789", -1),
        ("ghi789", "abc123", 1),
        ("def456", "ghi789", -1),
        ("ghi789", "def456", 1),
    ],
    ids=[
        "first_to_second",
        "second_to_first",
        "same_commit",
        "first_to_last",
        "last_to_first",
        "middle_to_last",
        "last_to_middle",
    ],
)
def test_git_versioning_strategy_compare(current, target, expected):
    """Test git version comparison based on commit history order."""
    commit_history = ["abc123", "def456", "ghi789"]
    strategy = GitVersioningStrategy(commit_history)
    assert strategy.compare_versions(current, target) == expected


def test_git_versioning_strategy_commit_not_in_history():
    """Test git versioning raises error when commit not in history."""
    commit_history = ["abc123", "def456", "ghi789"]
    strategy = GitVersioningStrategy(commit_history)

    with pytest.raises(ValueError, match="Failed to find commits in history"):
        strategy.compare_versions("xyz999", "def456")
