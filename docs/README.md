# SuperMedicine Documentation

Use this page as the entry point for maintained documentation.

Desktop GUI and OpenTUI are the primary interactive interfaces. Maintained
functions are available from both interfaces. Harness and RAG run continuously;
Multi-Agent and other extensions can be enabled or disabled.

## User guides

- [Installation](guides/INSTALL.md) is the canonical source for source installs,
  release archives, OpenTUI prerequisites, and uninstall behavior.
- [Getting started](guides/getting-started.md) covers the first project and core
  workflows.
- [Web and desktop UI](guides/WEB.md) covers local startup, remote access,
  security boundaries, and troubleshooting.
- [Examples](examples/README.md) links runnable and copyable examples.
- [References](references/README.md) contains research and figure guidance.

## Architecture

- [System architecture](architecture/ARCHITECTURE.md) defines component
  ownership and dependency boundaries.
- [Runtime pipeline](architecture/runtime-pipeline.md) defines mandatory
  Harness/RAG behavior and optional Multi-Agent execution.
- [Release architecture](architecture/release-architecture.md) defines Wheel,
  sdist, executable, archive, and publication boundaries.

## Maintainers

- [Maintainer index](maintainers/README.md)
- [Repository map](maintainers/repository-map.md)
- [Quality gates](maintainers/quality-gates.md)
- [CI workflows](maintainers/ci-workflows.md)
- [Project debug and repair record](maintainers/debugging.md)
- [Feature parity](maintainers/feature-parity.md)

Formal documents are indexed by `manifest.yaml`. Adapter skill and agent
Markdown files are runtime resources and intentionally remain outside the
formal-document manifest.
