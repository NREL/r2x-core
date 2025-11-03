"""Tests for r2x_core.System class."""

from pathlib import Path

import pytest
from infrasys import Component, SingleTimeSeries
from infrasys.exceptions import ISFileExists

from r2x_core import System


@pytest.fixture
def example_system():
    return System(100.0, name="TestSystem", description="A test system")


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


def test_system_accessors(example_system):
    """Test creating system with description."""
    system = example_system
    assert system.name == "TestSystem"
    assert system.description == "A test system"
    assert system.base_power == 100.0


def test_system_str_representation(example_system):
    """Test string representation."""
    system = example_system
    str_repr = str(system)
    assert "TestSystem" in str_repr
    assert "System" in str_repr
    assert repr(system) == str(system)


@pytest.mark.parametrize(
    "fname",
    ["system_json.json", Path("system.json")],
    ids=["str_path", "pathlib_path"],
)
def test_to_json_with_fname(fname, tmp_path, example_system):
    import json

    system = example_system
    out_path = tmp_path / fname
    system.to_json(out_path, overwrite=True, indent=2)
    assert out_path.exists()
    content = json.loads(out_path.read_text())
    assert "name" in content.get("system", content)


def test_to_json_with_no_args(example_system):
    import orjson

    system = example_system

    json_str = system.to_json()
    assert isinstance(json_str, bytes)
    json_deserialized = orjson.loads(json_str)
    assert "name" in json_deserialized
    assert json_deserialized["name"] == "TestSystem"


def test_roundtrip_serialization(tmp_path):
    """Test complete save/load roundtrip."""
    original = System(name="RoundtripTest", description="Testing roundtrip")

    original.add_components(Component(name="dummy"))
    file_path = tmp_path / "roundtrip.json"
    original.to_json(file_path)
    loaded = System.from_json(file_path)

    assert loaded.name == original.name
    assert loaded.description == original.description
    assert len(list(loaded.get_components(Component))) == 1


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


def test_to_json_bytes_with_time_series(caplog):
    """Test serializing system with time series to stdout."""
    from datetime import datetime, timedelta

    import numpy as np

    original_system = System(name="TestSystem", description="Test stdout with time series")

    component = Component(name="TestComponent")
    original_system.add_components(component)
    ts_data = SingleTimeSeries.from_array(
        data=np.array([1.0, 2.0, 3.0, 4.0, 5.0]),
        name="test_variable",
        initial_timestamp=datetime(2024, 1, 1),
        resolution=timedelta(hours=1),
    )
    original_system.add_time_series(ts_data, component)

    json_bytes = original_system.to_json()

    deserialized_system = System.from_json(json_bytes)
    assert isinstance(deserialized_system, System)
    assert deserialized_system.uuid == original_system.uuid
    component_deserialized = deserialized_system.get_component(Component, name="TestComponent")
    assert deserialized_system.has_time_series(component_deserialized)
