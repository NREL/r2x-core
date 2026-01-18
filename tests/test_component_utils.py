from infrasys import Component

from r2x_core.component_utils import components_to_records, export_components_to_csv
from r2x_core.system import System


def test_components_to_records_returns_data():
    """Test components_to_records returns list of dictionaries."""
    system = System(name="TestSystem")
    system.add_components(Component(name="comp1"), Component(name="comp2"))

    result = components_to_records(system)
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

    result = components_to_records(system, filter_func=lambda c: "keep" in c.name)
    assert len(result) == 2
    assert all("keep" in r["name"] for r in result)


def test_components_to_records_with_fields():
    """Test components_to_records with specific fields."""
    system = System(name="FieldsTest")
    system.add_components(Component(name="test"))

    # Only export name field
    result = components_to_records(system, fields=["name"])
    assert len(result) == 1
    assert "name" in result[0]
    # Should only have the name field
    assert len(result[0]) == 1


def test_components_to_records_with_key_mapping():
    """Test components_to_records with key mapping."""
    system = System(name="MappingTest")
    system.add_components(Component(name="test"))

    result = components_to_records(system, key_mapping={"name": "component_name"})
    assert len(result) == 1
    assert "component_name" in result[0]
    assert result[0]["component_name"] == "test"


def test_export_components_to_csv_to_file(tmp_path):
    """Test export_components_to_csv to file."""
    import csv

    system = System(name="FileTest")
    system.add_components(Component(name="comp1"), Component(name="comp2"))

    output_file = tmp_path / "components.csv"
    export_components_to_csv(system, file_path=output_file)

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
    export_components_to_csv(system, file_path=output_file, filter_func=lambda c: False)

    assert not output_file.exists()
