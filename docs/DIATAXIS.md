# Documentation Structure (Diátaxis Framework)

This document explains how the r2x-core documentation is organized according to the [Diátaxis](https://diataxis.fr/) framework.

## The Four Types of Documentation

### 📚 Tutorials (Learning-Oriented)
**Purpose**: Take users by the hand through a series of steps to complete a project.

**Characteristics**:
- Learning by doing
- Get started with practical steps
- Safe to explore and make mistakes
- Show what's possible

**In r2x-core**: *(Coming soon)*
- Getting started with r2x-core
- Building your first parser
- Creating a complete model translation workflow

---

### 🔧 How-To Guides (Task-Oriented)
**Purpose**: Show how to solve a specific problem or accomplish a particular task.

**Characteristics**:
- Practical, goal-oriented
- Assume some knowledge
- Multiple ways to achieve the goal
- Recipes for specific situations

**In r2x-core**:
- `how-tos/plugin-registration.md` - Registering plugins
- `how-tos/plugin-usage.md` - Using registered plugins
- `how-tos/filter-examples.md` - Filter registry examples
- `how-tos/parser-basics.md` - Creating parsers
- `how-tos/exporter-basics.md` - Creating exporters
- `how-tos/system-operations.md` - Working with systems
- `how-tos/datafile-basics.md` - Configuring data files
- `how-tos/datastore-management.md` - Managing data stores

---

### 💡 Explanations (Understanding-Oriented)
**Purpose**: Explain concepts, provide background, and clarify design decisions.

**Characteristics**:
- Deepen understanding
- Provide context and background
- Explain alternatives and trade-offs
- Discuss the "why" not just the "how"

**In r2x-core**:
- `explanations/plugin-system.md` - Plugin system architecture and design
  - Why three plugin types?
  - Why singleton pattern?
  - Why flexible signatures?
  - Entry point discovery mechanism
  - Security considerations
  - Design trade-offs

---

### 📖 Reference (Information-Oriented)
**Purpose**: Provide technical descriptions of how things work.

**Characteristics**:
- Austere and to the point
- Structure determined by the code
- Comprehensive and accurate
- API documentation

**In r2x-core**:
- `references/api/` - Auto-generated API documentation
- `references/file-types.md` - File type reference
- `references/exceptions.md` - Exception reference

## Documentation Map for Plugin System

Here's how plugin system documentation is distributed:

```
Plugin System Documentation
│
├── Explanation (Understanding)
│   └── explanations/plugin-system.md
│       ├── Architecture overview
│       ├── Design decisions
│       ├── Plugin types explained
│       ├── Why singleton?
│       ├── Why flexible signatures?
│       └── Security & future considerations
│
├── How-To Guides (Tasks)
│   ├── how-tos/plugin-registration.md
│   │   ├── Register model plugins
│   │   ├── Register system modifiers
│   │   ├── Register filters
│   │   └── Create external packages
│   │
│   ├── how-tos/plugin-usage.md
│   │   ├── Discover plugins
│   │   ├── Load parsers/exporters
│   │   ├── Apply modifiers
│   │   └── Use filters
│   │
│   └── how-tos/filter-examples.md
│       ├── Basic filters
│       ├── Chaining filters
│       ├── Advanced patterns
│       └── Parser integration
│
└── Reference (API)
    └── references/api/plugins.rst
        ├── PluginManager
        ├── PluginComponent
        └── SystemModifier protocol
```

## When to Use Each Type

### Use Tutorials When:
- You're new to r2x-core
- You want to learn by doing
- You need a safe environment to explore
- You want to see what's possible

### Use How-To Guides When:
- You have a specific task to accomplish
- You know what you want to do but not how
- You need a recipe or example
- You're solving a practical problem

### Use Explanations When:
- You want to understand design decisions
- You need context about why things work this way
- You're evaluating whether r2x-core fits your needs
- You want to contribute and need to understand architecture

### Use Reference When:
- You need precise technical information
- You're looking up a specific API
- You need complete parameter documentation
- You want to verify exact behavior

## Contributing Documentation

When adding new documentation, ask:

**Is this teaching a complete beginner?**
→ Add a Tutorial

**Is this showing how to solve a specific problem?**
→ Add a How-To Guide

**Is this explaining why something is the way it is?**
→ Add an Explanation

**Is this documenting what exists technically?**
→ Add to Reference (or auto-generate from docstrings)

## Further Reading

- [Diátaxis Framework](https://diataxis.fr/)
- [The Grand Unified Theory of Documentation](https://www.writethedocs.org/videos/eu/2017/the-four-kinds-of-documentation-and-why-you-need-to-understand-what-they-are-daniele-procida/)
