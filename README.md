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
  <a href="https://join.slack.com/t/datarobot-community/shared_invite/zt-3uzfp8k50-SUdMqeux25ok9_5wr4okrg">
    <img src="https://img.shields.io/badge/%23applications-a?label=Slack&labelColor=30373D&color=81FBA6" alt="Slack #applications">
  </a>
  <img src="https://img.shields.io/badge/status-beta-orange" alt="Beta">
</p>

> [!NOTE]
> This project is in **beta**. APIs, configuration, and outputs may change between releases.

The agent evaluation component for DataRobot App Framework projects. It batch-tests agent responses at scale using the [NeMo Evaluator](https://github.com/NVIDIA-NeMo/evaluator) **BYOB** (Bring Your Own Benchmark) framework.

App developers use it to regression-test agents after model or prompt changes, run safety and quality checks, and compare versions against a fixed dataset. It treats the agent as a black box&mdash;only the final OpenAI-compatible response is scored.

This repository ships the **Copier template** (`template/`) that renders into a project, plus the **user-facing documentation** in `template/docs/evaluation/` (rendered to `docs/evaluation/` in an installed project).

**What it does**: Sends each test prompt to the agent's OpenAI-compatible endpoint (black-box), then scores the agent's response. It ships **8 isolated benchmarks**&mdash;pick one per run via a pipeline YAML. Three are **judge-based** (LLM-as-judge: `answer_quality`, `safety_refusal`, `faithfulness`) and five are **judge-free** (deterministic, no judge model needed: `answer_correctness`, `instruction_following`, `prompt_injection`, `pii_leakage`, `tool_grounding`). Output is normalized to a stable JSON schema.

# Table of contents

- [Prerequisites](#prerequisites)
- [Quick start](#quick-start)
- [Component dependencies](#component-dependencies)
- [Authentication and configuration](#authentication-and-configuration)
- [Documentation](#documentation)
- [Updating](#updating)
- [Troubleshooting](#troubleshooting)
- [Next steps and cross-links](#next-steps-and-cross-links)
- [Contributing, changelog, support, and legal](#contributing-changelog-support-and-legal)

# Prerequisites

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/) and [`uvx`](https://docs.astral.sh/uv/guides/tools/) installed.
- [`dr`](https://cli.datarobot.com) installed (for `dr component add` and `dr task`).
- A DataRobot account with API access and a valid API token (for judge-based benchmarks and dataset generation).

# Quick start

Run the following command in your project directory:

```bash
dr component add https://github.com/datarobot-community/af-component-evaluation .
```

If you need additional control, run Copier directly:

```bash
uvx copier copy datarobot-community/af-component-evaluation .
```

After the wizard completes, the project contains the evaluation component ready for customization. Run a first evaluation from the component directory:

```bash
task install
task eval -- \
  --endpoint http://localhost:8842/v1 \
  --pipeline answer_quality.yaml \
  --dataset  user_datasets/sample_answer_quality.json \
  --dry-run
```

Set `DATAROBOT_API_TOKEN` and `DATAROBOT_ENDPOINT` in the project-root `.env` before judge-based runs. See [Getting started](template/docs/evaluation/getting-started.md) for the full walkthrough.

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

User-facing documentation ships with the component in [`template/docs/evaluation/`](template/docs/evaluation/) and is rendered to `docs/evaluation/` in your project.

| Page | What it covers |
|------|----------------|
| [Getting started](template/docs/evaluation/getting-started.md) | Install through your first completed run. |
| [Overview](template/docs/evaluation/README.md) | Start here; index of everything below. |
| [Benchmarks](template/docs/evaluation/benchmarks.md) | The 8 built-in benchmarks and what each scores. |
| [Pipelines](template/docs/evaluation/pipelines.md) | Configuring a run with a pipeline YAML. |
| [Datasets](template/docs/evaluation/datasets.md) | Test case format and required fields. |
| [Outputs](template/docs/evaluation/outputs.md) | Result schema, scoring, inconclusive cases. |
| [Writing your own benchmark](template/docs/evaluation/writing-benchmarks.md) | Custom scorers. |
| [Troubleshooting](template/docs/evaluation/troubleshooting.md) | Judge-model gotchas and known limits. |
| [NAT vs. NeMo](template/docs/evaluation/nat-vs-nemo.md) | How this differs from NVIDIA NAT `/evaluate`. |

Developing this component itself is covered in [DEVELOPMENT.md](DEVELOPMENT.md).

# Updating

All components should be regularly updated to pick up bug fixes, new features, and compatibility with the latest DataRobot App Framework.

For automatic updates to the latest version, run the following command in your project directory:

```bash
dr component update .datarobot/answers/evaluation-[[ evaluation_app_name ]].yml
```

For finer control with Copier directly:

```bash
uvx copier update -a .datarobot/answers/evaluation-[[ evaluation_app_name ]].yml -A
```

# Troubleshooting

Common issues when running or developing this component:

| Symptom | Likely cause | Fix |
|---|---|---|
| Judge returns 400 on Bedrock models | NeMo sends both `temperature` and `top_p`. | Use an Azure GPT judge in the pipeline YAML. |
| Wrong judge model name | LiteLLM `datarobot/` prefix used against the gateway. | Use gateway catalog names (for example `azure/gpt-5-5-2026-04-23`). |
| Cases marked inconclusive on safety runs | Judge endpoint content-filtered the adversarial prompt. | Expected behavior&mdash;see [Outputs](template/docs/evaluation/outputs.md). |
| `task eval` cannot reach agent | Agent not running or wrong port. | Start the agent (`dr run dev`) and confirm `http://localhost:8842/v1`. |

Full troubleshooting guide: [template/docs/evaluation/troubleshooting.md](template/docs/evaluation/troubleshooting.md).

# Next steps and cross-links

- [Getting started](template/docs/evaluation/getting-started.md)&mdash;first evaluation run.
- [NAT vs. NeMo](template/docs/evaluation/nat-vs-nemo.md)&mdash;when to use batch output testing vs. NAT `/evaluate`.
- [Writing your own benchmark](template/docs/evaluation/writing-benchmarks.md)&mdash;custom BYOB scorers.
- [DataRobot App Framework documentation](https://af.datarobot.com)&mdash;component model and CLI.
- [NeMo Evaluator BYOB](https://github.com/NVIDIA-NeMo/evaluator)&mdash;underlying benchmark framework.

# Contributing, changelog, support, and legal

See [AUTHORS](AUTHORS) and [LICENSE](LICENSE) for authorship and licensing.

To contribute, fork the repository, make your changes on a branch, and open a pull request. Ensure `task test` passes before submitting. See [CONTRIBUTING.md](.github/CONTRIBUTING.md) for additional guidelines, and [DEVELOPMENT.md](DEVELOPMENT.md) for the component internals.

For support, see the [troubleshooting guide](template/docs/evaluation/troubleshooting.md) or [contact DataRobot](https://docs.datarobot.com/en/docs/get-started/troubleshooting/general-help.html).
