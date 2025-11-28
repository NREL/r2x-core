"""Tests for :mod:`r2x_core.upgrader_utils` helpers."""

from r2x_core.upgrader_utils import (
    UpgradeStep,
    UpgradeType,
    run_upgrade_step,
    shall_we_upgrade,
)
from r2x_core.versioning import SemanticVersioningStrategy


def _dummy_step(
    *,
    target_version: str = "2.0",
    min_version: str | None = None,
    max_version: str | None = None,
) -> UpgradeStep:
    return UpgradeStep(
        name="dummy",
        func=lambda data: data,
        target_version=target_version,
        upgrade_type=UpgradeType.FILE,
        min_version=min_version,
        max_version=max_version,
    )


def test_shall_we_upgrade_below_minimum_returns_false():
    step = _dummy_step(target_version="3.0", min_version="2.0")
    strategy = SemanticVersioningStrategy()

    result = shall_we_upgrade(step, current_version="1.5", strategy=strategy)
    assert result.is_ok()
    assert result.value is False


def test_shall_we_upgrade_above_maximum_returns_false():
    step = _dummy_step(target_version="10.0", max_version="5.0")
    strategy = SemanticVersioningStrategy()

    result = shall_we_upgrade(step, current_version="6.0", strategy=strategy)
    assert result.is_ok()
    assert result.value is False


def test_shall_we_upgrade_within_range_returns_true():
    step = _dummy_step(target_version="3.0", min_version="1.0", max_version="4.0")
    strategy = SemanticVersioningStrategy()

    result = shall_we_upgrade(step, current_version="2.0", strategy=strategy)
    assert result.is_ok()
    assert result.value is True


def test_run_upgrade_step_passes_context_when_supported():
    def step_func(data, upgrader_context=None):
        assert upgrader_context == {"info": "value"}
        return data + 1

    step = UpgradeStep(
        name="context-step",
        func=step_func,
        target_version="1.0",
        upgrade_type=UpgradeType.FILE,
    )

    result = run_upgrade_step(step, data=41, upgrader_context={"info": "value"})
    assert result.is_ok()
    assert result.value == 42


def test_run_upgrade_step_wraps_exceptions():
    def broken_step(data):
        raise RuntimeError("boom")

    step = UpgradeStep(
        name="broken-step",
        func=broken_step,
        target_version="1.0",
        upgrade_type=UpgradeType.FILE,
    )

    result = run_upgrade_step(step, data="ignored")
    assert result.is_err()
    assert "Failed broken-step" in result.err()
