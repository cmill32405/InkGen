# InkGen Documentation

InkGen is a Python toolkit for procedurally generating richly annotated SVG drawings. It combines reusable geometric components, document abstractions, styling primitives, and text layout utilities that are tailored for engineering diagrams and synthetic data generation pipelines.

This documentation is organised around three primary goals:

1. **Understand the architecture** – learn how drawings are composed from components, layers, and documents.
2. **Build practical drawings** – follow guides that walk through creating SVG output using the provided APIs and examples.
3. **Reference the API surface** – discover the public classes, functions, and configuration points exposed under `InkGen`.

If you are new to InkGen, start with [Getting Started](getting-started.md) to install the toolkit and generate your first drawing. Then explore the [Components](components/drawing-components.md) section to understand the primitives available for building documents.

```mermaid
graph LR
    A[Components] --> B[ComponentGroup]
    B --> C[Layer]
    C --> D[Document]
    D --> E[DocumentSVG]
    E --> F[SVG Output]
```

The codebase is split between the core package located in `src/InkGen/` and runnable examples in the `examples/` directory. Formal tests live in `tests/` and act as an executable specification of the API.

## Support and Feedback

InkGen is an evolving project. If you run into issues or have questions:

- Open an issue in the GitHub repository.
- Start a discussion about feature ideas or architectural questions.
- Submit pull requests – contributions are welcome and appreciated.

Before contributing, please review the [contributing guidelines](../CONTRIBUTING.md).
