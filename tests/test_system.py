"""Tests for r2x_core.System class."""

import csv
import json
from datetime import datetime, timedelta

import numpy as np
import pytest
from infrasys import Component
from infrasys.exceptions import ISFileExists
from infrasys.time_series_models import SingleTimeSeries

from r2x_core import System


def test_system_creation():
    """Test creating a system instance."""
    system = System(name="TestSystem")
    assert system.name == "TestSystem"
    assert isinstance(system, System)


def test_to_json_raises_on_existing_file_without_overwrite(tmp_path):
    """Test that to_json raises error when file exists and overwrite=False."""

    system = System(name="TestSystem")
    output_file = tmp_path / "system.json"
    system.to_json(output_file)

    with pytest.raises(ISFileExists):
        system.to_json(output_file, overwrite=False)


def test_system_with_description():
    """Test creating system with description."""
    system = System(name="TestSystem", description="A test system")
    assert system.name == "TestSystem"
    assert system.description == "A test system"


def test_system_auto_add_composed():
    """Test system with auto_add_composed_components."""
    system = System(name="TestSystem", auto_add_composed_components=True)
    assert system.name == "TestSystem"


def test_system_str_representation():
    """Test string representation."""
    system = System(name="TestSystem")
    str_repr = str(system)
    assert "TestSystem" in str_repr
    assert "System" in str_repr


def test_system_repr():
    """Test repr is same as str."""
    system = System(name="TestSystem")
    assert repr(system) == str(system)


def test_to_json(tmp_path):
    """Test serializing system to JSON."""
    system = System(name="TestSystem", description="Test")
    output_file = tmp_path / "system.json"

    system.to_json(output_file)
    assert output_file.exists()


def test_from_json(tmp_path):
    """Test deserializing system from JSON."""
    system = System(name="TestSystem", description="Test")

    system.add_components(Component(name="dummy"))

    output_file = tmp_path / "system.json"
    system.to_json(output_file)

    loaded_system = System.from_json(output_file)
    assert loaded_system.name == "TestSystem"
    assert loaded_system.description == "Test"


def test_roundtrip_serialization(tmp_path):
    """Test complete save/load roundtrip."""
    original = System(name="RoundtripTest", description="Testing roundtrip")

    original.add_components(Component(name="dummy"))
    file_path = tmp_path / "roundtrip.json"
    original.to_json(file_path)
    loaded = System.from_json(file_path)

    assert loaded.name == original.name
    assert loaded.description == original.description


def test_to_json_with_overwrite(tmp_path):
    """Test overwriting existing JSON file."""
    system1 = System(name="System1")
    system2 = System(name="System2")
    system1.add_components(Component(name="dummy1"))
    system2.add_components(Component(name="dummy2"))
    output_file = tmp_path / "system.json"

    system1.to_json(output_file)
    assert output_file.exists()

    system2.to_json(output_file, overwrite=True)

    loaded = System.from_json(output_file)
    assert loaded.name == "System2"


def test_to_json_no_overwrite_raises(tmp_path):
    """Test that to_json raises error when file exists and overwrite=False."""
    system = System(name="TestSystem")
    output_file = tmp_path / "system.json"

    system.to_json(output_file)

    with pytest.raises(ISFileExists):
        system.to_json(output_file, overwrite=False)


def test_to_json_stdout(capsys):
    """Test serializing system to stdout."""
    import json

    system = System(name="TestSystem", description="Test stdout")
    system.to_json()

    captured = capsys.readouterr()
    output_data = json.loads(captured.out)

    assert output_data["name"] == "TestSystem"
    assert output_data["description"] == "Test stdout"
    assert "uuid" in output_data
    assert "components" in output_data


def test_to_json_stdout_with_indent(capsys):
    """Test serializing system to stdout with indentation."""
    import json

    system = System(name="TestSystem", description="Test stdout with indent")

    system.to_json(indent=2)

    captured = capsys.readouterr()
    output_data = json.loads(captured.out)

    assert output_data["name"] == "TestSystem"
    assert output_data["description"] == "Test stdout with indent"

    assert "\n" in captured.out


def test_to_json_stdout_with_time_series(capsys):
    """Test serializing system with time series to stdout."""
    system = System(name="TestSystem", description="Test stdout with time series")

    component = Component(name="TestComponent")
    system.add_components(component)
    ts_data = SingleTimeSeries.from_array(
        data=np.array([1.0, 2.0, 3.0, 4.0, 5.0]),
        name="test_variable",
        initial_timestamp=datetime(2024, 1, 1),
        resolution=timedelta(hours=1),
    )
    system.add_time_series(ts_data, component)

    system.to_json()

    captured = capsys.readouterr()
    output_data = json.loads(captured.out)

    assert output_data["name"] == "TestSystem"
    assert "time_series" in output_data
    assert "directory" in output_data["time_series"]


def test_components_to_records_returns_data():
    """Test components_to_records returns list of dictionaries."""

    system = System(name="TestSystem")
    system.add_components(Component(name="comp1"), Component(name="comp2"))

    result = system.components_to_records()
    assert isinstance(result, list)
    assert len(result) == 2


def test_components_to_records_with_filter():
    """Test components_to_records with filter function."""

    system = System(name="FilterTest")
    system.add_components(
        Component(name="keep1"),
        Component(name="skip"),
        Component(name="keep2"),
    )

    result = system.components_to_records(filter_func=lambda c: "keep" in c.name)
    assert len(result) == 2
    assert all("keep" in r["name"] for r in result)


def test_components_to_records_with_fields():
    """Test components_to_records with specific fields."""

    system = System(name="FieldsTest")
    system.add_components(Component(name="test"))

    # Only export name field
    result = system.components_to_records(fields=["name"])
    assert len(result) == 1
    assert "name" in result[0]
    # Should only have the name field
    assert len(result[0]) == 1


def test_components_to_records_with_key_mapping():
    """Test components_to_records with key mapping."""

    system = System(name="MappingTest")
    system.add_components(Component(name="test"))

    result = system.components_to_records(key_mapping={"name": "component_name"})
    assert len(result) == 1
    assert "component_name" in result[0]
    assert result[0]["component_name"] == "test"


def test_export_components_to_csv_to_file(tmp_path):
    """Test export_components_to_csv to file."""
    system = System(name="FileTest")
    system.add_components(Component(name="comp1"), Component(name="comp2"))

    output_file = tmp_path / "components.csv"
    system.export_components_to_csv(output_file)

    assert output_file.exists()

    # Read and verify CSV
    with open(output_file) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 2
        assert rows[0]["name"] == "comp1"
        assert rows[1]["name"] == "comp2"


def test_export_components_to_csv_empty(tmp_path):
    """Test export_components_to_csv when no components match."""

    system = System(name="EmptyTest")
    system.add_components(Component(name="test"))

    output_file = tmp_path / "empty.csv"
    system.export_components_to_csv(output_file, filter_func=lambda c: False)

    assert not output_file.exists()
