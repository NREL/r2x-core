# Welcome to `r2x-core` documentation!

R2X Core is the foundational framework and engine for building power system model translators. It provides the core infrastructure, data models, and APIs that enable translation between different power system modeling platforms.

## Framework Overview

R2X Core serves as the base layer for the R2X ecosystem, providing:

- **Core Data Models**: Standardized representations of power system components
- **Base Classes**: Abstract interfaces for parsers and exporters
- **Configuration Management**: Flexible configuration system for translation workflows
- **Plugin Architecture**: Extensible framework for adding new model support

The actual model parsers and exporters are implemented in separate packages that build upon this core package.

## Roadmap

If you're curious about what we're working on, check out the roadmap:

- [Active issues](https://github.com/NREL/r2x-core/issues?q=is%3Aopen+is%3Aissue+label%3A%22Working+on+it+%F0%9F%92%AA%22+sort%3Aupdated-asc): Issues that we are actively working on.
- [Prioritized backlog](https://github.com/NREL/r2x-core/issues?q=is%3Aopen+is%3Aissue+label%3ABacklog): Issues we'll be working on next.
- [Nice-to-have](https://github.com/NREL/r2x-core/labels/Optional): Nice to have features or Issues to fix. Anyone can start working on (please let us know before you do).
- [Ideas](https://github.com/NREL/r2x-core/issues?q=is%3Aopen+is%3Aissue+label%3AIdea): Future work or ideas for R2X Core.

## Core Components

### Base Parser Interface

```{eval-rst}
.. autosummary::
   :nosignatures:

   ~r2x_core.parser.handler.BaseParser
```

### Base Exporter Interface

```{eval-rst}
.. autosummary::
   :nosignatures:

   ~r2x_core.exporter.handler.BaseExporter
```

## Framework Compatibility

| R2X Core Version | Infrasys Version | Python Version |
| ---------------- | ---------------- | -------------- |
| 0.0.1            | Latest           | 3.10 - 3.13    |

```{toctree}
:hidden: true
docs/source/install.md
docs/source/howtos.md
docs/source/troubleshoot.md
```

```{toctree}
:caption: Developer Guide
:hidden: true

docs/source/contributing.md
docs/source/dev/develop.md
docs/source/dev/git.md
```

```{toctree}
:caption: Core Framework
:hidden: true

docs/source/model/logic.md
docs/source/model/diagram.md
docs/source/model/models.md
docs/source/model/data_models.md
docs/source/model/terminology.md
```

```{toctree}
:caption: API Documentation
:hidden: true

docs/source/api/enums.md
docs/source/api/config.md
docs/source/api/system.md
docs/source/api/models.md
docs/source/api/parsers.md
docs/source/api/exporters.md
```
