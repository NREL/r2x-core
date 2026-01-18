# R2X Documentation Conventions

This document establishes the standard format and style for all R2X Core documentation, organized by Diátaxis document type.

## General Style Rules

| Rule                          | Convention                                                                         |
| ----------------------------- | ---------------------------------------------------------------------------------- |
| **No emojis or icons**        | Never use emojis, unicode icons, or decorative symbols                             |
| **No ASCII diagrams**         | Use `{mermaid}` blocks when diagrams help clarify flow                             |
| **Prose over bullets**        | Default to paragraphs; bullets only for reference lists, summaries, and "See Also" |
| **Cross-references**          | Use `{doc}` and `{py:class}` (MyST syntax with build-time validation)              |
| **Code in tutorials/how-tos** | `python doctest` format with `>>>` prompts (testable)                              |
| **Code in explanations**      | Plain `python` blocks (illustrative, not necessarily runnable)                     |
| **Closing section**           | Always "See Also" (tutorials may also have "Next Steps" before it)                 |

---

## Object References

Always use proper MyST Sphinx cross-reference syntax when mentioning Python objects. This ensures references are hyperlinked and validated at build time.

| Object Type | Syntax       | Example                                           |
| ----------- | ------------ | ------------------------------------------------- |
| Class       | `{py:class}` | `` {py:class}`~r2x_core.DataStore` ``             |
| Function    | `{py:func}`  | `` {py:func}`~r2x_core.apply_rules_to_context` `` |
| Method      | `{py:meth}`  | `` {py:meth}`~r2x_core.DataStore.read_data` ``    |
| Module      | `{py:mod}`   | `` {py:mod}`r2x_core.units` ``                    |
| Attribute   | `{py:attr}`  | `` {py:attr}`~r2x_core.DataFile.name` ``          |
| Exception   | `{py:exc}`   | `` {py:exc}`~r2x_core.PluginError` ``             |

**Key rules:**

- Use the tilde `~` prefix to display only the short name (e.g., `DataStore` instead of `r2x_core.DataStore`)
- Never use plain inline code (`` `DataStore` ``) when referring to an actual API object
- These references are validated at build time, catching broken links early

**Example:**

```markdown
The {py:class}`~r2x_core.DataStore` class manages multiple data files. Use {py:meth}`~r2x_core.DataStore.read_data` to load a file.
```

---

## Text and Math

Use plain ASCII text and MathTeX for mathematical expressions. Never use unicode-only symbols.

| Content          | Convention                                           |
| ---------------- | ---------------------------------------------------- |
| **Plain text**   | ASCII only, no unicode symbols                       |
| **Math**         | Markdown MathTeX with `$` for inline, `$$` for block |
| **Arrows**       | Use prose or diagrams instead of unicode arrows      |
| **Math symbols** | Use MathTeX ($\geq$, $\sqrt{x}$) instead of unicode  |
| **Bullets**      | Standard markdown `-` or `*`, not unicode bullets    |
| **Quotes**       | Standard `"` and `'`, not fancy unicode quotes       |

**Inline math:**

```markdown
The power equation is $P = VI\cos\theta$ where $\theta$ is the phase angle.
```

**Block math:**

```markdown
$$
S = \sqrt{P^2 + Q^2}
$$
```

**Avoid:**

- Unicode arrows: `→`, `←`, `↔` (use prose or diagrams instead)
- Unicode math: `∑`, `∫`, `√`, `≥`, `≤` (use MathTeX)
- Unicode bullets: `•`, `◦`, `▪` (use standard markdown `-` or `*`)
- Fancy quotes: `"`, `"`, `'`, `'` (use standard `"` and `'`)

---

## Tutorials (Learning-Oriented)

**Purpose**: Step-by-step lessons that teach concepts by building something concrete.

### Structure

````markdown
# <Action Verb> <What You'll Build/Learn>

<1-2 sentence description of what the reader will accomplish.>

## Prerequisites

- R2X Core installed: `pip install r2x-core`
- <Any other requirements>

## <Step 1: Verb Phrase>

<Brief context paragraph>

```python doctest
>>> from r2x_core import DataFile  # doctest: +SKIP
>>> # Working, testable example
```
````

## <Step 2: Verb Phrase>

...

## Summary

<What you learned, 2-3 bullet points>

## Next Steps

- {doc}`./related-tutorial` - Continue learning with...
- {doc}`../how-tos/task-name` - Apply what you learned

## See Also

- {doc}`../explanations/topic` - Background context
- {py:class}`~r2x_core.ClassName` - API reference

````

### Conventions

- **Title format**: Action verb + what you build (e.g., "Build Your First Plugin", "Create a System Translator")
- **Length**: 100-200 lines (substantial but focused)
- **Code**: All `python doctest` format with `>>>` prompts
- **Tone**: Second person ("you will learn"), encouraging
- **Diagrams**: Yes, for lifecycle or multi-step flows
- **Bullet points**: Only in Summary section
- **Required sections**: Prerequisites, 2-5 numbered/named steps, Summary, Next Steps, See Also

---

## How-To Guides (Task-Oriented)

**Purpose**: Concise recipes for accomplishing specific tasks. Assume reader knows the basics.

### Structure

```markdown
# <Verb> <Object>

<1-sentence description of what this guide accomplishes.>

## <Primary Task>

```python doctest
>>> from r2x_core import DataFile  # doctest: +SKIP
>>> # Minimal working example
```

## <Variation or Edge Case> (optional)

```python doctest
>>> # Alternative approach
```

## See Also

- {doc}`./related-howto` - Related task
- {py:class}`~r2x_core.ClassName` - API reference

````

### Conventions

- **Title format**: Verb + noun (e.g., "Read Data Files", "Apply Translation Rules", "Configure Plugin Defaults")
- **Length**: 50-100 lines (concise, scannable)
- **Code**: All `python doctest` format with `>>>` prompts
- **Tone**: Direct, imperative ("Use X to accomplish Y")
- **Diagrams**: Rarely (keep focused on the task)
- **Bullet points**: Only in See Also
- **Required sections**: Primary task(s), optional variations, always end with "See Also"
- **Do NOT include**: Lengthy explanations (link to Explanations docs instead)

---

## Explanations (Understanding-Oriented)

**Purpose**: Background and context about design decisions and architecture.

### Structure

````markdown
# <Topic> Architecture

<Opening paragraph explaining what this document covers and why it matters.>

## Overview

<High-level summary of the system/concept>

## Core Concepts

### <Concept 1>

<Prose explanation with optional untested code example>

```python
# Illustrative example (not necessarily runnable)
class Example:
    ...
```
````

### <Concept 2>

...

## Design Decisions

### Why <Decision>?

<Rationale, trade-offs considered, alternatives rejected>

## Trade-offs

<Honest discussion of limitations and when this approach may not fit>

## See Also

- {doc}`../how-tos/topic/task` - Practical usage
- {doc}`../tutorials/tutorial-name` - Learn by doing
- {py:class}`~r2x_core.ClassName` - API reference

````

### Conventions

- **Title format**: Noun phrase + context (e.g., "Plugin System Architecture", "Data Management Design Philosophy")
- **Length**: 150-350 lines (comprehensive but not exhaustive)
- **Code**: Plain `python` blocks (illustrative, not doctest)
- **Tone**: Third person, analytical ("The system uses...", "This design enables...")
- **Diagrams**: Yes, for architecture and data flow
- **Bullet points**: Only for quick reference lists
- **Required sections**: Overview, Core Concepts, Design Decisions, Trade-offs, See Also
- **Must have**: At least one "Why X?" section explaining rationale

---

## References (Information-Oriented)

**Purpose**: Technical descriptions of APIs. Dry, accurate, complete.

### Structure

```markdown
# <Module/Class Name>

<One-line description of purpose.>

## Quick Reference

- {py:class}`~r2x_core.ClassName` - Brief description
- {py:func}`~r2x_core.function_name` - Brief description

## API Documentation

```{eval-rst}
.. autoclass:: r2x_core.ClassName
   :members:
   :show-inheritance:
````

## See Also

- {doc}`./related-reference` - Related module
- {doc}`../explanations/topic` - Background context

````

### Conventions

- **Title format**: Exact class/module name (e.g., "System", "DataStore", "Plugin API")
- **Length**: Variable (driven by autodoc output)
- **Code**: `{eval-rst}` autodoc directives only (documentation lives in source code)
- **Tone**: Neutral, factual
- **Diagrams**: No
- **Bullet points**: Only in Quick Reference list
- **Required sections**: Quick Reference (bullet list), API Documentation, See Also
- **Do NOT include**: Tutorials or how-to content (link out instead)

---

## Diagrams

Use `{mermaid}` when a diagram genuinely clarifies flow or architecture. Do not use diagrams for anything explainable in 1-2 sentences.

### When to Use Diagrams

- Lifecycle hooks or execution order
- Data flow between components
- Architecture with multiple interacting pieces
- State machines or decision flows

### When NOT to Use Diagrams

- Simple linear processes (prose is clearer)
- Anything explainable in 1-2 sentences

### Syntax

```markdown
```{mermaid}
flowchart TD
    A[Input] --> B[Process]
    B --> C[Output]
````

````

---

## Prose Style

Write full paragraphs for explanatory content. Reserve bullets for enumeration where the list structure itself carries meaning.

### Correct (Prose)

```markdown
## Why Lazy Evaluation?

The DataStore uses lazy evaluation because large projects often configure hundreds of data files but only need a subset in any given run. Without lazy loading, you'd pay the cost of reading all files upfront. Lazy evaluation also localizes errors: if a data file is broken, you discover it only when you try to read it. This is actually desirable when certain files are optional. Finally, lazy loading enables composition: you can create a DataStore with all possible files, then selectively read based on runtime parameters like solver year or scenario.
````

### Incorrect (Over-Bulleted)

```markdown
## Why Lazy Evaluation?

- Efficiency: Large projects might configure hundreds of files
- Error Localization: Broken files discovered only when read
- Composition: Create DataStore with all files, read selectively
```

---

## Index Pages

Each section index should follow this structure:

````markdown
# <Section Name>

<One paragraph explaining the purpose of this section and when to use it.>

## Categories (if applicable)

```{toctree}
:maxdepth: 1

category/page1
category/page2
```
````

## When to Use This Section

<Bullet list distinguishing from other sections>
```

---

## Quick Reference by Document Type

| Aspect            | Tutorial                      | How-To          | Explanation        | Reference      |
| ----------------- | ----------------------------- | --------------- | ------------------ | -------------- |
| **Purpose**       | Learn by doing                | Task recipe     | Understand design  | API lookup     |
| **Title**         | Verb + what you build         | Verb + noun     | Noun + context     | Exact name     |
| **Length**        | 100-200 lines                 | 50-100 lines    | 150-350 lines      | Variable       |
| **Code examples** | Doctest (`>>>`)               | Doctest (`>>>`) | Plain Python       | Autodoc only   |
| **Tone**          | 2nd person                    | Imperative      | Analytical         | Factual        |
| **Diagrams**      | Yes (flow/lifecycle)          | Rarely          | Yes (architecture) | No             |
| **Bullets**       | Summary only                  | See Also only   | Ref lists only     | Ref list only  |
| **Must have**     | Prerequisites, steps, summary | Primary task    | Design rationale   | Quick Ref, API |

---

## Examples

For concrete examples of each document type following these conventions, see:

- **Tutorial**: `docs/source/tutorials/working-with-units.md`
- **How-To**: `docs/source/how-tos/read-data-files.md`
- **Explanation**: `docs/source/explanations/data-management.md`
- **Reference**: `docs/source/references/models.md`
