<p align="center">
    <picture>
      <source media="(prefers-color-scheme: dark)" srcset="docs/_static/scaffold_logo_black.png" width="200">
      <source media="(prefers-color-scheme: light)" srcset="docs/_static/scaffold_logo_white.png" width="200">
      <img alt="Scaffold Logo" src="https://docs.scaffold.merantix-momentum.cloud/_static/scaffold_logo_white.png" width="200">
    </picture>
    <h2 align="center">Scaffold Core</h2>
</p>

Scaffold is the foundational Python package for all AI development at Merantix Momentum. It provides the "scaffolding" to accelerate building, deploying, and orchestrating AI systems on our platform.

This library is **opinionated** by design. It contains a collection of wrappers, convenience functions, and boilerplate code that enforce our best practices and ensure seamless integration between our most-used tools (like Flyte, PyTorch, and internal platform services).

## 🚀 Key Features

**⚡ Accelerate Development:** Reduces boilerplate for common tasks like data handling, configuration management, and model orchestration
**🧩 Modular Installation:** Install only the dependencies you need using "extras" (e.g., flyte, torch)
**⚙️ Standardized:** Enforces Merantix Momentum's processes for building and scaling AI projects
**🔗 Platform Integration:** Provides simple, high-level APIs for interacting with the Merantix Momentum AI Platform


## 📦 Installation

```bash
    pip install mxm-scaffold
```

The base package is lightweight. You install additional functionality via "extras".

Install the extras you need for your project. For example, to install the Flyte and PyTorch utilities:
```bash
    # To use Flyte for orchestration
    pip install mxm-scaffold[flyte]

    # To use PyTorch utilities
    pip install mxm-scaffold[torch]

    # To install everything (common for development)
    pip install mxm-scaffold[all]
```

### Available extras:
* *data:* Data handling, datasets, and dataloaders
* *flyte:* Utilities for working with Flyte
* *torch:* Utilities for working with PyTorch
* *monitoring:* Utilities for monitoring training jobs
* *wandb:* Utilities for logging to Weights and Biases
* *dev:* Dependencies required for development and running tests
* *all:* Installs all extras

## 📖 Documentation

If you work at Merantix Momentum, you can visit additional documentation via https://docs.scaffold.merantix-momentum.cloud/.

The documentation is built & deployed for the main-branch and tags.
[Please find more information about documentation here](<https://docs.scaffold.merantix-momentum.cloud/usage/document.html>).

Alternatively, build the publicly available documentation locally:

    cd scaffold/docs
    make html


## 🤝 Contributing

This is an internal tool, and contributions from all teams are welcome!

[Check the documentation for more information on how to contribute](<https://docs.scaffold.merantix-momentum.cloud/usage/contribute.html>).
