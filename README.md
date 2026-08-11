<p align="center">
  <a href="https://github.com/datarobot-community/af-component-evaluation">
    <img src="https://af.datarobot.com/img/datarobot_logo.avif" width="600px" alt="DataRobot Logo"/>
  </a>
</p>
<p align="center">
    <span style="font-size: 1.5em; font-weight: bold; display: block;">af-component-evaluation</span>
</p>

<p align="center">
  <a href="https://datarobot.com">Homepage</a>
  ·
  <a href="https://af.datarobot.com">Documentation</a>
  ·
  <a href="https://docs.datarobot.com/en/docs/get-started/troubleshooting/general-help.html">Support</a>
</p>

<p align="center">
  <a href="https://github.com/datarobot-community/af-component-evaluation/tags">
    <img src="https://img.shields.io/github/v/tag/datarobot-community/af-component-evaluation?label=version" alt="Latest Release">
  </a>
  <a href="/LICENSE">
    <img src="https://img.shields.io/github/license/datarobot-community/af-component-evaluation" alt="License">
  </a>
  <img src="https://img.shields.io/badge/status-beta-orange" alt="Beta">
</p>

> [!NOTE]
> This project is in **beta**. It is under active development and the APIs, configuration, and outputs may change between releases.

Batch evaluation component for DataRobot agents using the [NeMo Evaluator](https://github.com/NVIDIA-NeMo/evaluator) **BYOB** (Bring Your Own Benchmark) framework.

**What it does:** sends each test prompt to the agent's OpenAI-compatible endpoint (black-box), then scores the agent's response. It ships **8 isolated benchmarks** — pick one per run via a pipeline YAML. Three are **judge-based** (LLM-as-judge: `answer_quality`, `safety_refusal`, `faithfulness`) and five are **judge-free** (deterministic, no judge model needed: `answer_correctness`, `instruction_following`, `prompt_injection`, `pii_leakage`, `tool_grounding`). Output is normalized to a stable JSON schema.

# Table of contents

- [Prerequisites](#prerequisites)
- [Quick start](#quick-start)
- [Component dependencies](#component-dependencies)
- [Authentication and configuration](#authentication-and-configuration)
- [Documentation](#documentation)
- [Contributing, changelog, support, and legal](#contributing-changelog-support-and-legal)

# Prerequisites

The following tools are required before applying this component.

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) and [`uvx`](https://docs.astral.sh/uv/guides/tools/) installed.
- [`dr`](https://cli.datarobot.com) installed.
- A DataRobot account with API access and a valid API token.

# Quick start

Run the following command in your project directory:

```bash
dr component add https://github.com/datarobot-community/af-component-evaluation .
```

If you need additional control, you can run this to use copier directly:

```bash
uvx copier copy datarobot-community/af-component-evaluation .
```

After the wizard completes, your project directory contains the evaluation component files ready for customization and deployment.

# Component dependencies

## Required

The following components must be applied to the project **before** this component:

| Name | Repository | Repeatable |
|------|-----------|------------|
| `base` | [https://github.com/datarobot-community/af-component-base](https://github.com/datarobot-community/af-component-base) | No |

# Authentication and configuration

Set the following environment variables before running or deploying the agent:

```bash
export DATAROBOT_ENDPOINT=https://app.datarobot.com/api/v2
export DATAROBOT_API_TOKEN=YOUR_API_TOKEN
```

You can also place these in a `.env` file at the root of your project instead of exporting them in your shell.

# Documentation

User-facing documentation ships with the component in
[`template/docs/evaluation/`](template/docs/evaluation/) and is rendered to
`docs/evaluation/` in your project.

| Page | What it covers |
|------|----------------|
| [Overview](template/docs/evaluation/README.md) | Start here; index of everything below |
| [Benchmarks](template/docs/evaluation/benchmarks.md) | The 8 built-in benchmarks and what each scores |
| [Pipelines](template/docs/evaluation/pipelines.md) | Configuring a run with a pipeline YAML |
| [Datasets](template/docs/evaluation/datasets.md) | Test case format and required fields |
| [Outputs](template/docs/evaluation/outputs.md) | Result schema, scoring, inconclusive cases |
| [Writing your own benchmark](template/docs/evaluation/writing-benchmarks.md) | Custom scorers |
| [Troubleshooting](template/docs/evaluation/troubleshooting.md) | Judge-model gotchas and known limits |
| [NAT vs. NeMo](template/docs/evaluation/nat-vs-nemo.md) | How this differs from NVIDIA NAT `/evaluate` |

Developing this component itself is covered in [DEVELOPMENT.md](DEVELOPMENT.md).

# Contributing, changelog, support, and legal

See [AUTHORS](AUTHORS) and [LICENSE](LICENSE) for authorship and licensing information.

To contribute, fork the repository, make your changes on a branch, and open a pull request. Ensure `task test` passes before submitting. See [CONTRIBUTING.md](.github/CONTRIBUTING.md) for additional guidelines, and [DEVELOPMENT.md](DEVELOPMENT.md) for the component internals.

For support, see the [troubleshooting guide](template/docs/evaluation/troubleshooting.md) or [contact DataRobot](https://docs.datarobot.com/en/docs/get-started/troubleshooting/general-help.html).
