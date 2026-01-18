# Rule System Architecture

This document explains the design philosophy and implementation of the rule-based translation system in R2X Core. For practical usage, see the {doc}`../how-tos/define-rule-mappings` guide.

## Purpose and Motivation

Power system model translation involves converting components from one modeling format to another. A generator in ReEDS has different field names, units, and structures than a generator in PLEXOS or Sienna. The {py:class}`~r2x_core.Rule` class provides a declarative way to express these transformations without writing procedural code for each source-target pair.

Traditional approaches to model translation often involve hard-coded conversion functions. Each source format requires a dedicated function that manually maps fields, handles edge cases, and creates target components. This approach creates several problems. Adding a new target format requires writing new functions for every source format. Changes to source or target schemas require updating multiple locations. Testing becomes difficult because conversion logic is scattered across many functions. Operator precedence and evaluation order can become ambiguous as the number of translation paths grows.

The rule system addresses these challenges through declarative specifications that separate the "what" from the "how." A {py:class}`~r2x_core.Rule` declares what transformation should happen. The {py:func}`~r2x_core.apply_rules_to_context` executor handles how to perform it.

## Core Design Principles

### Declarative Over Imperative

Rules describe what transformation should happen rather than how to perform it step by step. A rule declares that a `BusComponent` should become a `NodeComponent` with field `kv_rating` mapped to `voltage_kv`. The rule executor handles the mechanics of reading source fields, applying conversions, and creating target instances.

This separation allows rules to be expressed in configuration files, versioned alongside data, and validated statically before execution. The {py:meth}`~r2x_core.Rule.from_records` method enables loading rules from JSON, making translation logic configurable without code changes.

### Composition Through Filters

Rather than embedding conditional logic within rules, the system uses composable {py:class}`~r2x_core.RuleFilter` objects to restrict which components a rule processes. A filter can match components by field values, by name prefixes, or by complex boolean combinations using `any_of` and `all_of`.

Filters are separate objects that rules reference, enabling reuse across multiple rules. A filter matching "all generators with capacity above 100 MW in region 'West'" can be defined once and applied to multiple translation rules. Changes to selection criteria require updating only the filter definition. This composition avoids the combinatorial explosion that would result from hardcoding each source/target/filter combination.

### Immutability for Correctness

{py:class}`~r2x_core.Rule` instances are frozen dataclasses that cannot be modified after creation. This immutability prevents subtle bugs where shared rules are accidentally modified, causing unexpected behavior in seemingly unrelated translations. Each rule application works with the exact configuration that was defined, making behavior reproducible and debugging straightforward.

The immutability constraint also enables safe sharing of rules across threads and processes. Concurrent translation operations cannot interfere with each other through shared mutable state. This is particularly important in enterprise environments where translation pipelines run continuously on large numbers of systems.

## Architecture Overview

### Rule Definition

The {py:class}`~r2x_core.Rule` class encapsulates a single transformation between source and target types. Each rule specifies the source component type (or types) it matches, the target type (or types) it produces, and a version number for schema evolution. The `field_map` dictionary describes how source fields become target fields, supporting both simple one-to-one mappings and complex multi-field derivations through getter functions.

Rules support several advanced features. The `defaults` parameter provides fallback values when source fields are missing, enabling translation from simpler models that lack detail. The `depends_on` parameter ensures rules execute in the correct order when target fields come from previously translated components. The `filter` parameter references a {py:class}`~r2x_core.RuleFilter` that restricts which source components the rule processes.

### Filter Predicates

The {py:class}`~r2x_core.RuleFilter` class provides a flexible predicate language for component selection. Leaf filters compare a component field against values using operations like equality, membership, numeric comparison, or prefix matching. Compound filters combine multiple predicates with `any_of` (OR) or `all_of` (AND) semantics.

The filter implementation optimizes for repeated evaluation. String values are casefolded once during filter construction rather than on every comparison. Prefix lists are cached in normalized form. These optimizations matter when filtering thousands of components during a large system translation.

### Rule Execution

The {py:func}`~r2x_core.apply_rules_to_context` function orchestrates the translation process. It first validates rules for consistency, checking for duplicate names and unresolved dependencies. Rules are then topologically sorted so that dependencies execute before dependents. Each rule is applied to all matching source components, creating target components that are added to the target system.

The function returns a {py:class}`~r2x_core.TranslationResult` containing detailed statistics. Individual rule outcomes are captured in {py:class}`~r2x_core.RuleResult` objects, providing visibility into what succeeded, what failed, and why. This detailed reporting enables debugging of translation workflows and monitoring of translation quality.

### Single-Rule Application

The {py:func}`~r2x_core.apply_single_rule` function handles translation for a single rule. It resolves source and target types, evaluates filters, builds target field values, and creates target components. This function is useful when you need fine-grained control over the translation process or want to apply rules selectively outside the full workflow.

## Design Trade-offs

### Why Frozen Dataclasses?

Rules could have been regular mutable objects, allowing dynamic modification during translation. However, mutable rules create subtle bugs. A rule modified by one translation could affect subsequent translations in unexpected ways. Debugging becomes difficult because the rule state at failure time differs from its initial definition. Frozen dataclasses prevent these issues at the cost of requiring new {py:class}`~r2x_core.Rule` objects for any variation. In practice, rule objects are rarely modified after creation, making this cost acceptable.

### Why String-Based Type References?

Rules reference source and target types by string name rather than actual Python classes. This design enables rules to be defined in JSON configuration files where class objects cannot be represented. The executor resolves strings to classes at runtime using the {py:class}`~r2x_core.PluginContext` model registry. This late binding adds flexibility but means type errors are caught at execution rather than definition time. The trade-off favors runtime flexibility for configuration-driven use cases.

### Why Separate Filters from Rules?

Filter logic could have been embedded directly in rule definitions. However, separating {py:class}`~r2x_core.RuleFilter` objects provides several benefits. Filters can be reused across multiple rules without duplication. Filter logic can be tested independently from translation logic. Complex selection criteria have clear ownership rather than being scattered across rule definitions. This separation also enables future optimization such as filter merging and predicate pushdown.

## Integration with Plugin System

Rules integrate with the broader plugin system through the {py:class}`~r2x_core.PluginContext`. The context provides access to source and target systems, configuration, and the model registry for type resolution. Translation plugins define rules as part of their configuration and invoke the rule executor during the `on_translate` lifecycle hook.

This integration enables declarative plugin configuration. A translation plugin can be fully configured through JSON files specifying rules, filters, and field mappings. The plugin code becomes a thin wrapper that loads configuration and invokes {py:func}`~r2x_core.apply_rules_to_context`, with all translation logic expressed declaratively.

## Performance Considerations

The rule system is designed for large-scale translations involving thousands of components. Rule validation and dependency sorting happen once per translation, not per component. Filter predicates cache normalized values to avoid repeated computation. The executor minimizes object allocation by reusing context objects across rule applications.

For very large systems, the executor could be extended to parallelize independent rules. The current sequential execution is sufficient for typical use cases but the architecture does not preclude parallel execution. The immutability of rules is actually beneficial for parallelization, as there is no need for locking or synchronization.

## Extension Points

The rule system provides several extension points for future enhancement. Custom filter operations could be registered to extend the predicate language. Rule inheritance could allow base rules with shared mappings that derived rules extend. Bidirectional rules could support round-trip translation by defining both directions in a single specification. Transformation pipelines could combine rules from multiple plugins. These extensions would build on the existing architecture without fundamental changes.

## See Also

- {doc}`../how-tos/define-rule-mappings` for practical usage examples
- {doc}`./plugin-system` for understanding plugin integration
- {py:class}`~r2x_core.Rule` API reference
- {py:class}`~r2x_core.RuleFilter` API reference
- {py:func}`~r2x_core.apply_rules_to_context` API reference
- {py:class}`~r2x_core.TranslationResult` API reference
