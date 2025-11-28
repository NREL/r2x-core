"""Utils for our merging logic."""

from typing import Any


def override_dictionary(base: dict[str, Any], overrides: dict[str, Any]) -> dict[str, Any]:
    """Recurse and override base dictionary."""
    merged: dict[str, Any] = base.copy()

    for key, override_value in overrides.items():
        if key not in merged:
            merged[key] = override_value
            continue

        base_value = merged[key]

        # Simple case if both are dictionary
        if isinstance(base_value, dict) and isinstance(override_value, dict):
            merged[key] = override_dictionary(base_value, override_value)
            continue

        # Positional merge (list + list)
        if isinstance(base_value, list) and isinstance(override_value, list):
            combined_list: list[Any] = []

            min_len = min(len(base_value), len(override_value))
            # Merge overlapping index
            for index in range(min_len):
                base_item = base_value[index]
                override_item = override_value[index]

                if isinstance(base_item, dict) and isinstance(override_item, dict):
                    # Recurse for inner indexes
                    combined_list.append(override_dictionary(base_item, override_item))
                else:
                    combined_list.append(override_item)

            # Append remaining base items (if any)
            if len(base_value) > min_len:
                combined_list.extend(base_value[min_len:])

            # Append remaining override items (if any)
            if len(override_value) > min_len:
                combined_list.extend(override_value[min_len:])

            merged[key] = combined_list
            continue

        merged[key] = override_value

    return merged
