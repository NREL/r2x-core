"""Tests for serialization and deserialization of unit-aware models."""

from typing import Annotated

import pytest
from infrasys import Component

from r2x_core.system import System
from r2x_core.units import HasPerUnit, Unit, UnitSystem, set_unit_system


class Generator(HasPerUnit, Component):
    """Test generator model."""

    name: str
    base_power: Annotated[float, Unit("MVA")]
    rated_voltage: Annotated[float, Unit("kV")]
    rating: Annotated[float, Unit("pu", base="base_power")]
    voltage: Annotated[float, Unit("pu", base="rated_voltage")]


class Transformer(HasPerUnit, Component):
    """Test transformer model."""

    name: str
    base_power: Annotated[float, Unit("MVA")]
    high_voltage: Annotated[float, Unit("kV")]
    low_voltage: Annotated[float, Unit("kV")]
    impedance: Annotated[float, Unit("pu", base="base_power")]


def test_model_dump_basic():
    """Test model_dump() returns correct dict with float values."""
    gen = Generator(
        name="Gen1",
        base_power=100.0,
        rated_voltage=13.8,
        rating=0.8,
        voltage=1.05,
    )

    data = gen.model_dump()

    assert data["name"] == "Gen1"
    assert data["base_power"] == 100.0
    assert data["rated_voltage"] == 13.8
    assert data["rating"] == 0.8
    assert data["voltage"] == 1.05
    assert isinstance(data["rating"], float)
    assert isinstance(data["voltage"], float)


def test_model_dump_with_mode():
    """Test model_dump() with different modes."""
    gen = Generator(
        name="Gen1",
        base_power=100.0,
        rated_voltage=13.8,
        rating=0.8,
        voltage=1.05,
    )

    data_python = gen.model_dump(mode="python")
    assert data_python["rating"] == 0.8

    data_json = gen.model_dump(mode="json")
    assert data_json["rating"] == 0.8


def test_model_dump_exclude():
    """Test model_dump() with exclude parameter."""
    gen = Generator(
        name="Gen1",
        base_power=100.0,
        rated_voltage=13.8,
        rating=0.8,
        voltage=1.05,
    )

    data = gen.model_dump(exclude={"uuid", "rating"})

    assert "uuid" not in data
    assert "rating" not in data
    assert "name" in data
    assert "voltage" in data


def test_model_dump_include():
    """Test model_dump() with include parameter."""
    gen = Generator(
        name="Gen1",
        base_power=100.0,
        rated_voltage=13.8,
        rating=0.8,
        voltage=1.05,
    )

    data = gen.model_dump(include={"name", "rating", "voltage"})

    assert set(data.keys()) == {"name", "rating", "voltage"}
    assert data["rating"] == 0.8


def test_model_dump_exclude_unset():
    """Test model_dump() with exclude_unset parameter."""
    gen = Generator(
        name="Gen1",
        base_power=100.0,
        rated_voltage=13.8,
        rating=0.8,
        voltage=1.05,
    )

    data = gen.model_dump(exclude_unset=True)
    assert "rating" in data
    assert "voltage" in data


def test_model_dump_by_alias():
    """Test model_dump() with by_alias parameter."""
    gen = Generator(
        name="Gen1",
        base_power=100.0,
        rated_voltage=13.8,
        rating=0.8,
        voltage=1.05,
    )

    # Should work without aliases defined
    data = gen.model_dump(by_alias=True)
    assert data["rating"] == 0.8


def test_model_dump_json():
    """Test model_dump_json() serialization."""
    gen = Generator(
        name="Gen1",
        base_power=100.0,
        rated_voltage=13.8,
        rating=0.8,
        voltage=1.05,
    )

    json_str = gen.model_dump_json()

    assert isinstance(json_str, str)
    assert "Gen1" in json_str
    assert "0.8" in json_str
    assert "1.05" in json_str


def test_model_dump_json_indent():
    """Test model_dump_json() with indentation."""
    gen = Generator(
        name="Gen1",
        base_power=100.0,
        rated_voltage=13.8,
        rating=0.8,
        voltage=1.05,
    )

    json_str = gen.model_dump_json(indent=2)

    assert isinstance(json_str, str)
    assert "\n" in json_str  # Should have newlines due to indentation


def test_model_dump_after_natural_unit_input():
    """Test that model_dump() returns float after natural unit input."""
    gen = Generator(
        name="Gen1",
        base_power=100.0,
        rated_voltage=13.8,
        rating={"value": 80.0, "unit": "MVA"},  # Input as dict
        voltage={"value": 14.49, "unit": "kV"},  # Input as dict
    )

    data = gen.model_dump()

    # Should serialize as float (internal representation)
    assert isinstance(data["rating"], float)
    assert isinstance(data["voltage"], float)
    assert data["rating"] == 0.8
    assert data["voltage"] == pytest.approx(1.05, rel=0.01)


def test_deserialize_from_dict():
    """Test deserializing from dict."""
    data = {
        "name": "Gen1",
        "base_power": 100.0,
        "rated_voltage": 13.8,
        "rating": 0.8,
        "voltage": 1.05,
    }

    gen = Generator(**data)

    assert gen.name == "Gen1"
    assert gen.rating == 0.8
    assert gen.voltage == 1.05


def test_deserialize_from_model_dump():
    """Test round-trip: dump and reload."""
    gen1 = Generator(
        name="Gen1",
        base_power=100.0,
        rated_voltage=13.8,
        rating=0.8,
        voltage=1.05,
    )

    data = gen1.model_dump()
    gen2 = Generator.model_validate(data)

    assert gen2.name == gen1.name
    assert gen2.base_power == gen1.base_power
    assert gen2.rating == gen1.rating
    assert gen2.voltage == gen1.voltage


def test_deserialize_from_json():
    """Test deserializing from JSON string."""
    json_str = '{"name": "Gen1", "base_power": 100.0, "rated_voltage": 13.8, "rating": 0.8, "voltage": 1.05}'

    gen = Generator.model_validate_json(json_str)

    assert gen.name == "Gen1"
    assert gen.rating == 0.8
    assert gen.voltage == 1.05


def test_roundtrip_json():
    """Test full round-trip: object -> JSON -> object."""
    gen1 = Generator(
        name="Gen1",
        base_power=100.0,
        rated_voltage=13.8,
        rating=0.8,
        voltage=1.05,
    )

    json_str = gen1.model_dump_json()
    gen2 = Generator.model_validate_json(json_str)

    assert gen2.name == gen1.name
    assert gen2.rating == gen1.rating
    assert gen2.voltage == gen1.voltage


def test_system_serialization(tmp_path):
    """Test serializing a system with components."""
    system = System(name="TestSystem", system_base=200.0)

    gen1 = Generator(
        name="Gen1",
        base_power=100.0,
        rated_voltage=13.8,
        rating=0.8,
        voltage=1.05,
    )
    gen2 = Generator(
        name="Gen2",
        base_power=150.0,
        rated_voltage=22.0,
        rating={"value": 120.0, "unit": "MVA"},  # Natural units
        voltage=1.0,
    )
    tx = Transformer(
        name="TX1",
        base_power=100.0,
        high_voltage=138.0,
        low_voltage=13.8,
        impedance=0.1,
    )

    system.add_components(gen1, gen2, tx)

    assert gen1._get_system_base() == 200.0
    assert gen2._get_system_base() == 200.0
    assert tx._get_system_base() == 200.0

    fpath = tmp_path / "system.json"
    system.to_json(fpath)
    assert fpath.exists()

    system2 = System.from_json(fpath)
    assert system2.name == "TestSystem"
    assert system2.base_power == 200.0

    generators = list(system2.get_components(Generator))
    transformers = list(system2.get_components(Transformer))

    assert len(generators) == 2
    assert len(transformers) == 1

    gen1_back = system2.get_component(Generator, name="Gen1")
    assert gen1_back.base_power == 100.0
    assert gen1_back.rating == 0.8
    assert gen1_back.voltage == 1.05

    gen2_back = system2.get_component(Generator, name="Gen2")
    assert gen2_back.base_power == 150.0
    assert gen2_back.rating == 0.8  # Was converted from 120 MVA
    assert gen2_back.voltage == 1.0

    tx_back = transformers[0]

    tx_back = system2.get_component(Transformer, name="TX1")
    assert tx_back.name == "TX1"
    assert tx_back.impedance == 0.1

    assert gen1_back._get_system_base() == 200.0
    assert gen2_back._get_system_base() == 200.0
    assert tx_back._get_system_base() == 200.0


def test_serialization_preserves_display_mode():
    """Test that serialization works regardless of display mode."""
    set_unit_system(UnitSystem.NATURAL_UNITS)
    gen = Generator(
        name="Gen1",
        base_power=100.0,
        rated_voltage=13.8,
        rating=0.8,
        voltage=1.05,
    )
    data = gen.model_dump()

    assert data["rating"] == 0.8  # Not 80.0
    assert data["voltage"] == 1.05  # Not 14.49
    set_unit_system(UnitSystem.DEVICE_BASE)


def test_model_dump_combined_parameters():
    """Test model_dump() with multiple parameters combined."""
    gen = Generator(
        name="Gen1",
        base_power=100.0,
        rated_voltage=13.8,
        rating=0.8,
        voltage=1.05,
    )

    data = gen.model_dump(
        mode="python",
        include={"name", "base_power", "rating", "voltage"},
        exclude_none=True,
    )

    assert set(data.keys()) == {"name", "base_power", "rating", "voltage"}
    assert data["rating"] == 0.8
    assert data["voltage"] == 1.05


def test_validation_context_preserved():
    """Test that validation context is preserved during deserialization."""
    data = {
        "name": "Gen1",
        "base_power": 100.0,
        "rated_voltage": 13.8,
        "rating": 0.8,
        "voltage": 1.05,
    }

    gen = Generator.model_validate(data)

    assert gen.rating == 0.8
    assert gen.voltage == 1.05


def test_system_rejects_component_with_different_base():
    """Test that adding a component with different _system_base raises error."""
    system1 = System(name="System1", system_base=100.0)

    gen = Generator(
        name="Gen1",
        base_power=100.0,
        rated_voltage=13.8,
        rating=0.8,
        voltage=1.05,
    )

    system1.add_component(gen)
    assert gen._get_system_base() == 100.0

    system2 = System(name="System2", system_base=200.0)

    with pytest.raises(ValueError, match=r"already has _system_base=100\.0.*base=200\.0"):
        system2.add_component(gen)
