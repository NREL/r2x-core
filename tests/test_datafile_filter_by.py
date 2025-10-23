"""Test DataFile filter_by functionality with PluginConfig variables."""

import json
from pathlib import Path

import pytest

from r2x_core import DataStore, PluginConfig


class SampleConfig(PluginConfig):
    """Sample configuration for testing."""

    solve_year: int
    weather_year: int
    scenario: str = "base"


def test_filter_by_with_solve_year_substitution(tmp_path: Path):
    """Test that filter_by substitutes '{solve_year}' placeholder with config value."""
    csv_file = tmp_path / "generators.csv"
    csv_file.write_text("name,capacity,year\ngen1,100,2025\ngen2,200,2030\ngen3,150,2035\n")

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    mapping_file = config_dir / "file_mapping.json"
    mapping = [
        {
            "name": "generators",
            "fpath": str(csv_file),
            "filter_by": {"year": "{solve_year}"},
        }
    ]
    mapping_file.write_text(json.dumps(mapping))

    config = SampleConfig(solve_year=2030, weather_year=2012)

    import inspect

    original_getfile = inspect.getfile

    def mock_getfile(cls):
        return str(tmp_path / "config.py") if cls == SampleConfig else original_getfile(cls)

    inspect.getfile = mock_getfile
    try:
        store = DataStore.from_plugin_config(config, folder=tmp_path)
        data = store.read_data_file(name="generators", placeholders=config.model_dump())
        df = data.collect()

        assert len(df) == 1
        assert df["year"][0] == 2030
        assert df["name"][0] == "gen2"
    finally:
        inspect.getfile = original_getfile


def test_filter_by_with_multiple_config_variables(tmp_path: Path):
    """Test filter_by with multiple config variable substitutions."""
    csv_file = tmp_path / "data.csv"
    csv_file.write_text(
        "name,year,weather_year,scenario\n"
        "item1,2030,2012,base\n"
        "item2,2030,2012,high\n"
        "item3,2030,2007,base\n"
        "item4,2035,2012,base\n"
    )

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    mapping_file = config_dir / "file_mapping.json"
    mapping = [
        {
            "name": "filtered_data",
            "fpath": str(csv_file),
            "filter_by": {
                "year": "{solve_year}",
                "weather_year": "{weather_year}",
                "scenario": "{scenario}",
            },
        }
    ]
    mapping_file.write_text(json.dumps(mapping))

    config = SampleConfig(solve_year=2030, weather_year=2012, scenario="base")

    import inspect

    original_getfile = inspect.getfile
    inspect.getfile = lambda cls: (
        str(tmp_path / "config.py") if cls == SampleConfig else original_getfile(cls)
    )
    try:
        store = DataStore.from_plugin_config(config, folder=tmp_path)
        data = store.read_data_file(name="filtered_data", placeholders=config.model_dump())
        df = data.collect()

        assert len(df) == 1
        assert df["name"][0] == "item1"
        assert df["year"][0] == 2030
        assert df["weather_year"][0] == 2012
        assert df["scenario"][0] == "base"
    finally:
        inspect.getfile = original_getfile


def test_filter_by_with_config_variable_in_list(tmp_path: Path):
    """Test config variable substitution within list filters."""
    csv_file = tmp_path / "data.csv"
    csv_file.write_text("name,year\nitem1,2025\nitem2,2030\nitem3,2035\n")

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    mapping_file = config_dir / "file_mapping.json"
    mapping = [
        {
            "name": "multi_year",
            "fpath": str(csv_file),
            "filter_by": {"year": [2025, "{solve_year}"]},
        }
    ]
    mapping_file.write_text(json.dumps(mapping))

    config = SampleConfig(solve_year=2030, weather_year=2012)

    import inspect

    original_getfile = inspect.getfile
    inspect.getfile = lambda cls: (
        str(tmp_path / "config.py") if cls == SampleConfig else original_getfile(cls)
    )
    try:
        store = DataStore.from_plugin_config(config, folder=tmp_path)
        data = store.read_data_file(name="multi_year", placeholders=config.model_dump())
        df = data.collect()

        assert len(df) == 2
        assert set(df["year"]) == {2025, 2030}
    finally:
        inspect.getfile = original_getfile


def test_filter_by_backward_compatibility(tmp_path: Path):
    """Test that regular filter_by values work without config substitution."""
    csv_file = tmp_path / "data.csv"
    csv_file.write_text("name,year,status\nitem1,2025,active\nitem2,2030,inactive\nitem3,2030,active\n")

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    mapping_file = config_dir / "file_mapping.json"
    mapping = [
        {
            "name": "regular_filter",
            "fpath": str(csv_file),
            "filter_by": {"year": 2030, "status": "active"},
        }
    ]
    mapping_file.write_text(json.dumps(mapping))

    config = SampleConfig(solve_year=2025, weather_year=2012)

    import inspect

    original_getfile = inspect.getfile
    inspect.getfile = lambda cls: (
        str(tmp_path / "config.py") if cls == SampleConfig else original_getfile(cls)
    )
    try:
        store = DataStore.from_plugin_config(config, folder=tmp_path)
        # No placeholders needed for regular literal values
        data = store.read_data_file(name="regular_filter")
        df = data.collect()

        assert len(df) == 1
        assert df["name"][0] == "item3"
        assert df["year"][0] == 2030
        assert df["status"][0] == "active"
    finally:
        inspect.getfile = original_getfile


def test_filter_by_with_custom_config_fields(tmp_path: Path):
    """Test that config variable substitution works with any PluginConfig field names."""

    class CustomConfig(PluginConfig):
        model_year: int
        horizon_year: int

    csv_file = tmp_path / "data.csv"
    csv_file.write_text("name,model_year,horizon_year\nitem1,2030,2050\nitem2,2030,2040\nitem3,2025,2050\n")

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    mapping_file = config_dir / "file_mapping.json"
    mapping = [
        {
            "name": "custom_filter",
            "fpath": str(csv_file),
            "filter_by": {"model_year": "{model_year}", "horizon_year": "{horizon_year}"},
        }
    ]
    mapping_file.write_text(json.dumps(mapping))

    config = CustomConfig(model_year=2030, horizon_year=2050)

    import inspect

    original_getfile = inspect.getfile
    inspect.getfile = lambda cls: (
        str(tmp_path / "config.py") if cls == CustomConfig else original_getfile(cls)
    )
    try:
        store = DataStore.from_plugin_config(config, folder=tmp_path)
        data = store.read_data_file(name="custom_filter", placeholders=config.model_dump())
        df = data.collect()

        assert len(df) == 1
        assert df["name"][0] == "item1"
        assert df["model_year"][0] == 2030
        assert df["horizon_year"][0] == 2050
    finally:
        inspect.getfile = original_getfile


def test_filter_by_placeholder_without_substitutions_fails_gracefully(tmp_path: Path):
    """Test that placeholders without placeholders dict give helpful error message."""
    csv_file = tmp_path / "data.csv"
    csv_file.write_text("name,year\nitem1,2025\nitem2,2030\n")

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    mapping_file = config_dir / "file_mapping.json"
    mapping = [
        {
            "name": "test_data",
            "fpath": str(csv_file),
            "filter_by": {"year": "{solve_year}"},
        }
    ]
    mapping_file.write_text(json.dumps(mapping))

    config = SampleConfig(solve_year=2030, weather_year=2012)

    import inspect

    original_getfile = inspect.getfile
    inspect.getfile = lambda cls: (
        str(tmp_path / "config.py") if cls == SampleConfig else original_getfile(cls)
    )
    try:
        store = DataStore.from_plugin_config(config, folder=tmp_path)
        # Try to read without providing placeholders
        with pytest.raises(ValueError) as exc_info:
            store.read_data_file(name="test_data")

        error_msg = str(exc_info.value)
        assert "Found placeholder '{solve_year}'" in error_msg
        assert "no placeholders provided" in error_msg
        assert "read_data_file()" in error_msg
    finally:
        inspect.getfile = original_getfile


def test_filter_by_unknown_placeholder_fails_gracefully(tmp_path: Path):
    """Test that unknown placeholder names give helpful error message."""
    csv_file = tmp_path / "data.csv"
    csv_file.write_text("name,year\nitem1,2025\nitem2,2030\n")

    config_dir = tmp_path / "config"
    config_dir.mkdir()
    mapping_file = config_dir / "file_mapping.json"
    mapping = [
        {
            "name": "test_data",
            "fpath": str(csv_file),
            "filter_by": {"year": "{unknown_var}"},
        }
    ]
    mapping_file.write_text(json.dumps(mapping))

    config = SampleConfig(solve_year=2030, weather_year=2012)

    import inspect

    original_getfile = inspect.getfile
    inspect.getfile = lambda cls: (
        str(tmp_path / "config.py") if cls == SampleConfig else original_getfile(cls)
    )
    try:
        store = DataStore.from_plugin_config(config, folder=tmp_path)
        # Try to read with placeholders dict that doesn't include the placeholder
        with pytest.raises(ValueError) as exc_info:
            store.read_data_file(name="test_data", placeholders=config.model_dump())

        error_msg = str(exc_info.value)
        assert "Placeholder '{unknown_var}' not found" in error_msg
        assert "Available placeholders:" in error_msg
    finally:
        inspect.getfile = original_getfile
