# Contributing to InkGen

👋 Thanks for your interest in contributing! This document outlines the process
for proposing changes, reporting issues, and collaborating on new features.

## Table of Contents
1. [Ways to Contribute](#ways-to-contribute)
2. [Getting Started](#getting-started)
3. [Development Workflow](#development-workflow)
4. [Coding Standards](#coding-standards)
5. [Testing](#testing)
6. [Pull Request Checklist](#pull-request-checklist)
7. [Community Expectations](#community-expectations)

## Ways to Contribute
- Report bugs or propose enhancements via GitHub issues
- Improve documentation and examples
- Add tests that increase confidence in critical functionality
- Extend the drawing/component APIs with new capabilities

## Getting Started
1. Fork the repository and create a feature branch off `main`
2. Set up the development environment:
   ```bash
   python -m venv .venv
   . .venv/Scripts/activate   # or source .venv/bin/activate on macOS/Linux
   pip install -e .[dev]
   ```
3. Install additional tooling if desired (e.g., pre-commit hooks)

## Development Workflow
1. Create a descriptive branch name, e.g. `feature/text-outline-fixes`
2. Keep commits focused and well-documented
3. Run linting and formatting before opening a PR:
   ```bash
   ruff check .
   ruff format .
   ```
4. Run automated tests: `pytest --cov`
5. Add new tests or update existing ones when changing functionality
6. Update documentation or examples when behavior changes

## Coding Standards
- Follow the existing project structure under `src/InkGen/`
- Prefer pure Python typing annotations and keep public APIs typed
- Avoid introducing new runtime dependencies without discussion
- Use docstrings and inline comments sparingly to clarify non-obvious logic

## Testing
- Unit tests belong in `tests/`
- Example scripts in `examples/` should remain runnable without special setup
- Aim for meaningful coverage on critical components such as geometry and text-fitting logic

## Pull Request Checklist
- [ ] Lint (`ruff check .`) succeeds
- [ ] Code is formatted (`ruff format .`)
- [ ] Tests pass locally (`pytest`)
- [ ] Documentation/README updated if behavior or usage changes
- [ ] Example outputs refreshed when relevant
- [ ] PR description explains the change and links related issues

## Community Expectations
We follow the [Contributor Covenant](CODE_OF_CONDUCT.md). By contributing, you
agree to foster an inclusive, respectful environment. Please report incidents to
the maintainers listed in the Code of Conduct.

Thanks again for helping make InkGen better!
