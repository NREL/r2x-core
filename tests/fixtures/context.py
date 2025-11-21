from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from r2x_core import PluginConfig, TranslationContext

FIXTURE_MODEL_MODULES: tuple[str, ...] = (
    "fixtures.source_system",
    "fixtures.target_system",
)


def _build_config() -> PluginConfig:
    """Create a PluginConfig pointing at fixture component modules."""
    from r2x_core import PluginConfig

    return PluginConfig(models=FIXTURE_MODEL_MODULES)


def _build_translation_context(
    rules_simple,
    source_system,
    target_system,
) -> TranslationContext:
    from r2x_core import TranslationContext

    return TranslationContext(
        source_system=source_system,
        target_system=target_system,
        config=_build_config(),
        rules=rules_simple,
    )


@pytest.fixture
def context_example(
    rules_simple,
    source_system,
    target_system,
) -> TranslationContext:
    """TranslationContext with populated systems and fixture rules."""
    return _build_translation_context(rules_simple, source_system, target_system)
