"""Additional tests for versioning.py to improve coverage."""

from pathlib import Path

from r2x_core.versioning import (
    FileModTimeStrategy,
    GitVersioningStrategy,
    SemanticVersioningStrategy,
)


class MockObject:
    """Mock object with version attribute for testing."""

    def __init__(self, version=None):
        self.version = version


class MockGitObject:
    """Mock object with git_version attribute for testing."""

    def __init__(self, git_version=None):
        self.git_version = git_version


def test_semantic_versioning_get_version_from_object():
    strategy = SemanticVersioningStrategy()
    obj = MockObject(version="1.2.3")
    version = strategy.get_version(obj)
    assert version == "1.2.3"


def test_semantic_versioning_get_version_from_object_none():
    strategy = SemanticVersioningStrategy()
    obj = MockObject(version=None)
    version = strategy.get_version(obj)
    assert version is None


def test_semantic_versioning_get_version_from_string():
    strategy = SemanticVersioningStrategy()
    version = strategy.get_version("some_string")
    assert version is None


def test_semantic_versioning_get_version_from_path():
    strategy = SemanticVersioningStrategy()
    version = strategy.get_version(Path("/some/path"))
    assert version is None


def test_semantic_versioning_set_version_on_object():
    strategy = SemanticVersioningStrategy()
    obj = MockObject()
    updated = strategy.set_version(obj, "2.0.0")
    assert updated.version == "2.0.0"


def test_semantic_versioning_set_version_on_unsupported_type():
    strategy = SemanticVersioningStrategy()
    result = strategy.set_version("string_data", "2.0.0")
    assert result == "string_data"


def test_git_versioning_get_version_from_object():
    strategy = GitVersioningStrategy()
    obj = MockGitObject(git_version="abc123")
    version = strategy.get_version(obj)
    assert version == "abc123"


def test_git_versioning_get_version_from_object_none():
    strategy = GitVersioningStrategy()
    obj = MockGitObject(git_version=None)
    version = strategy.get_version(obj)
    assert version is None


def test_git_versioning_get_version_missing():
    strategy = GitVersioningStrategy()
    data = {"other": "data"}
    version = strategy.get_version(data)
    assert version is None


def test_git_versioning_set_version_on_object():
    strategy = GitVersioningStrategy()
    obj = MockGitObject()
    updated = strategy.set_version(obj, "def456")
    assert updated.git_version == "def456"


def test_git_versioning_set_version_on_unsupported_type():
    strategy = GitVersioningStrategy()
    result = strategy.set_version("string_data", "abc123")
    assert result == "string_data"


def test_git_versioning_compare_timestamps_current_none():
    strategy = GitVersioningStrategy(use_timestamps=True)
    result = strategy.compare(None, "2023-01-01T10:00:00Z")
    assert result == -1


def test_git_versioning_compare_timestamps_equal():
    strategy = GitVersioningStrategy(use_timestamps=True)
    timestamp = "2023-01-01T10:00:00Z"
    result = strategy.compare(timestamp, timestamp)
    assert result == 0


def test_git_versioning_compare_timestamps_greater():
    strategy = GitVersioningStrategy(use_timestamps=True)
    current = "2023-01-01T12:00:00Z"
    target = "2023-01-01T10:00:00Z"
    result = strategy.compare(current, target)
    assert result == 1


def test_git_versioning_compare_timestamps_invalid_format():
    strategy = GitVersioningStrategy(use_timestamps=True)
    result = strategy.compare("invalid-timestamp", "2023-01-01T10:00:00Z")
    assert result == -1


def test_git_versioning_compare_hashes_equal():
    strategy = GitVersioningStrategy()
    commit_hash = "abc123"
    result = strategy.compare(commit_hash, commit_hash)
    assert result == 0


def test_git_versioning_compare_hashes_greater():
    strategy = GitVersioningStrategy()
    result = strategy.compare("xyz789", "abc123")
    assert result == 1


def test_git_versioning_compare_hashes_none():
    strategy = GitVersioningStrategy()
    result = strategy.compare(None, "abc123")
    assert result == -1


def test_file_mod_time_strategy_set_version_warning():
    strategy = FileModTimeStrategy()
    data = {"some": "data"}
    result = strategy.set_version(data, "1234567890.0")
    assert result == data


def test_file_mod_time_strategy_compare_current_none():
    strategy = FileModTimeStrategy()
    result = strategy.compare(None, "1672531200.0")
    assert result == -1


def test_file_mod_time_strategy_compare_equal():
    strategy = FileModTimeStrategy()
    timestamp = "1672531200.0"
    result = strategy.compare(timestamp, timestamp)
    assert result == 0


def test_file_mod_time_strategy_compare_greater():
    strategy = FileModTimeStrategy()
    result = strategy.compare("1672531200.0", "1640995200.0")
    assert result == 1


def test_file_mod_time_strategy_compare_invalid_format():
    strategy = FileModTimeStrategy()
    result = strategy.compare("invalid-number", "1672531200.0")
    assert result == -1


def test_semantic_versioning_get_version_from_object_without_version_field():
    strategy = SemanticVersioningStrategy()
    obj = object()
    version = strategy.get_version(obj)
    assert version is None


def test_git_versioning_get_version_from_object_without_git_version_field():
    strategy = GitVersioningStrategy()
    obj = object()
    version = strategy.get_version(obj)
    assert version is None
