from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from r2x_core import TranslationContext


@pytest.fixture
def context(
    rules_simple,
) -> TranslationContext:
    """TranslationContext with mock systems and rules.

    Creates a complete TranslationContext for use in tests. All rules
    are indexed automatically by (source_type, target_type, version).

    Returns
    -------
    TranslationContext
        Ready-to-use context with all rules accessible

    Examples
    --------
    Basic usage:
    >>> rule = context.get_rule("Bus", "Node")

    Get specific version:
    >>> rule = context.get_rule("Bus", "Node", version=1)

    List all rules:
    >>> all_rules = context.list_rules()
    """
    from r2x_core import PluginConfig, System, TranslationContext

    return TranslationContext(
        source_system=System(name="Source"),
        target_system=System(name="Target"),
        config=PluginConfig(),
        rules=rules_simple,
    )
