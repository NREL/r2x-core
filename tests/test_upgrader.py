"""Tests for BaseUpgrader class and upgrade registration."""

import pytest

from r2x_core.upgrader import BaseUpgrader
from r2x_core.upgrader_utils import UpgradeStep, UpgradeType


class TestUpgraderDecoratorForm:
    """Test upgrader decorator registration forms."""

    def test_register_step_decorator_form(self):
        """Test registering a step using decorator form."""

        class MyUpgrader(BaseUpgrader):
            pass

        @MyUpgrader.register_step(
            name="upgrade_v1_to_v2",
            target_version="2.0",
            upgrade_type=UpgradeType.FILE,
        )
        def upgrade_func(data):
            return data

        assert len(MyUpgrader.steps) == 1
        assert MyUpgrader.steps[0].name == "upgrade_v1_to_v2"
        assert MyUpgrader.steps[0].target_version == "2.0"

    def test_register_step_direct_call_form(self):
        """Test registering a step using direct call form (not decorator)."""

        class MyUpgrader(BaseUpgrader):
            pass

        def upgrade_func(data):
            return data

        # Direct call form - func is not None
        result = MyUpgrader.register_step(
            upgrade_func,
            name="upgrade_v1_to_v2",
            target_version="2.0",
            upgrade_type=UpgradeType.FILE,
        )

        assert result is upgrade_func
        assert len(MyUpgrader.steps) == 1
        assert MyUpgrader.steps[0].name == "upgrade_v1_to_v2"

    def test_register_step_without_explicit_name_decorator(self):
        """Test decorator form uses function name if no name provided."""

        class MyUpgrader(BaseUpgrader):
            pass

        @MyUpgrader.register_step(
            target_version="2.0",
            upgrade_type=UpgradeType.FILE,
        )
        def my_upgrade_step(data):
            return data

        assert MyUpgrader.steps[0].name == "my_upgrade_step"

    def test_register_step_without_explicit_name_direct(self):
        """Test direct call form uses function name if no name provided."""

        class MyUpgrader(BaseUpgrader):
            pass

        def my_upgrade_step(data):
            return data

        MyUpgrader.register_step(
            my_upgrade_step,
            target_version="2.0",
            upgrade_type=UpgradeType.FILE,
        )

        assert MyUpgrader.steps[0].name == "my_upgrade_step"

    def test_register_step_multiple_steps(self):
        """Test registering multiple steps."""

        class MyUpgrader(BaseUpgrader):
            pass

        @MyUpgrader.register_step(name="step1", target_version="1.0", upgrade_type=UpgradeType.FILE)
        def step1(data):
            return data

        @MyUpgrader.register_step(name="step2", target_version="2.0", upgrade_type=UpgradeType.SYSTEM)
        def step2(data):
            return data

        assert len(MyUpgrader.steps) == 2
        assert MyUpgrader.steps[0].name == "step1"
        assert MyUpgrader.steps[1].name == "step2"

    def test_register_step_isolation_between_subclasses(self):
        """Test that steps are isolated between subclasses."""

        class Upgrader1(BaseUpgrader):
            pass

        class Upgrader2(BaseUpgrader):
            pass

        @Upgrader1.register_step(name="step1", target_version="1.0", upgrade_type=UpgradeType.FILE)
        def step1(data):
            return data

        @Upgrader2.register_step(name="step2", target_version="2.0", upgrade_type=UpgradeType.SYSTEM)
        def step2(data):
            return data

        assert len(Upgrader1.steps) == 1
        assert len(Upgrader2.steps) == 1
        assert Upgrader1.steps[0].name == "step1"
        assert Upgrader2.steps[0].name == "step2"

    def test_list_steps(self):
        """Test list_steps returns registered steps."""

        class MyUpgrader(BaseUpgrader):
            pass

        @MyUpgrader.register_step(name="step1", target_version="1.0", upgrade_type=UpgradeType.FILE)
        def step1(data):
            return data

        steps = MyUpgrader.list_steps()
        assert len(steps) == 1
        assert isinstance(steps[0], UpgradeStep)
        assert steps[0].name == "step1"

    def test_register_step_preserves_function_name_decorator(self):
        """Test that decorator returns the original function."""

        class MyUpgrader(BaseUpgrader):
            pass

        @MyUpgrader.register_step(name="test_step", target_version="1.0", upgrade_type=UpgradeType.FILE)
        def my_func(data):
            """My function docstring."""
            return data

        assert my_func.__name__ == "my_func"
        assert my_func.__doc__ == "My function docstring."

    def test_register_step_preserves_function_name_direct(self):
        """Test that direct call returns the original function."""

        class MyUpgrader(BaseUpgrader):
            pass

        def my_func(data):
            """My function docstring."""
            return data

        result = MyUpgrader.register_step(
            my_func,
            name="test_step",
            target_version="1.0",
            upgrade_type=UpgradeType.FILE,
        )

        assert result is my_func
        assert result.__name__ == "my_func"

    def test_register_step_with_extra_kwargs_decorator(self):
        """Test decorator with extra kwargs passed to UpgradeStep."""

        class MyUpgrader(BaseUpgrader):
            pass

        @MyUpgrader.register_step(
            name="step1",
            target_version="2.0",
            upgrade_type=UpgradeType.FILE,
            priority=50,
            min_version="1.0",
            max_version="3.0",
        )
        def upgrade_step(data):
            return data

        step = MyUpgrader.steps[0]
        assert step.priority == 50
        assert step.min_version == "1.0"
        assert step.max_version == "3.0"

    def test_register_step_with_extra_kwargs_direct(self):
        """Test direct call with extra kwargs passed to UpgradeStep."""

        class MyUpgrader(BaseUpgrader):
            pass

        def upgrade_step(data):
            return data

        MyUpgrader.register_step(
            upgrade_step,
            name="step1",
            target_version="2.0",
            upgrade_type=UpgradeType.FILE,
            priority=75,
        )

        step = MyUpgrader.steps[0]
        assert step.priority == 75

    def test_subclass_inherits_empty_steps(self):
        """Test that each subclass starts with empty steps."""

        class Upgrader1(BaseUpgrader):
            pass

        class Upgrader2(BaseUpgrader):
            pass

        # Both should have empty lists initially
        assert len(Upgrader1.steps) == 0
        assert len(Upgrader2.steps) == 0

    def test_decorator_with_callable_function(self):
        """Test decorator works with various callable types."""

        class MyUpgrader(BaseUpgrader):
            pass

        # Test with lambda (unusual but valid)
        lambda_func = lambda data: data  # noqa: E731

        result = MyUpgrader.register_step(
            lambda_func,
            name="lambda_step",
            target_version="1.0",
            upgrade_type=UpgradeType.FILE,
        )

        assert len(MyUpgrader.steps) == 1
        assert MyUpgrader.steps[0].name == "lambda_step"


class TestUpgradeStepCreation:
    """Test UpgradeStep object creation via register_step."""

    def test_upgrade_step_has_correct_attributes(self):
        """Test that created UpgradeStep has correct attributes."""

        class MyUpgrader(BaseUpgrader):
            pass

        @MyUpgrader.register_step(
            name="test_step",
            target_version="2.0",
            upgrade_type=UpgradeType.SYSTEM,
            priority=25,
            min_version="1.5",
            max_version="2.5",
        )
        def upgrade_func(data):
            return data

        step = MyUpgrader.steps[0]
        assert isinstance(step, UpgradeStep)
        assert step.name == "test_step"
        assert step.target_version == "2.0"
        assert step.upgrade_type == UpgradeType.SYSTEM
        assert step.priority == 25
        assert step.min_version == "1.5"
        assert step.max_version == "2.5"
        assert callable(step.func)

    def test_register_step_without_name_filters_correctly(self):
        """Test that 'name' kwarg is filtered out when passed to UpgradeStep."""

        class MyUpgrader(BaseUpgrader):
            pass

        @MyUpgrader.register_step(
            name="explicit_name",
            target_version="1.0",
            upgrade_type=UpgradeType.FILE,
        )
        def func(data):
            return data

        # Should not raise TypeError about unexpected 'name' argument
        step = MyUpgrader.steps[0]
        assert step.name == "explicit_name"


class TestUpgraderSubclassing:
    """Test BaseUpgrader subclassing behavior."""

    def test_multiple_independent_upgraders(self):
        """Test multiple upgraders can coexist independently."""

        class Upgrader1(BaseUpgrader):
            pass

        class Upgrader2(BaseUpgrader):
            pass

        class Upgrader3(BaseUpgrader):
            pass

        @Upgrader1.register_step(name="v1_step", target_version="1.0", upgrade_type=UpgradeType.FILE)
        def step1(data):
            return data

        @Upgrader2.register_step(name="v2_step", target_version="2.0", upgrade_type=UpgradeType.SYSTEM)
        def step2(data):
            return data

        assert len(Upgrader1.steps) == 1
        assert len(Upgrader2.steps) == 1
        assert len(Upgrader3.steps) == 0

    def test_parent_and_child_upgraders_isolated(self):
        """Test parent and child upgraders maintain separate step lists."""

        class ParentUpgrader(BaseUpgrader):
            pass

        class ChildUpgrader(ParentUpgrader):
            pass

        @ParentUpgrader.register_step(name="parent_step", target_version="1.0", upgrade_type=UpgradeType.FILE)
        def parent_step(data):
            return data

        @ChildUpgrader.register_step(name="child_step", target_version="2.0", upgrade_type=UpgradeType.SYSTEM)
        def child_step(data):
            return data

        assert len(ParentUpgrader.steps) == 1
        assert len(ChildUpgrader.steps) == 1
        assert ParentUpgrader.steps[0].name == "parent_step"
        assert ChildUpgrader.steps[0].name == "child_step"
