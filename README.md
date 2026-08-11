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

# Table of contents

- [Prerequisites](#prerequisites)
- [Quick start](#quick-start)
- [Component dependencies](#component-dependencies)
- [Local development](#local-development)
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

# Local development

This README targets **developers of `af-component-evaluation` itself**. User-facing documentation that ships with the rendered component lives in **`template/docs/evaluation/`** &rarr; **`docs/evaluation/`** after install.

| Doc | Purpose |
|---|---|
| [Getting started](template/docs/evaluation/getting-started.md) | Install through first completed run. |
| [Evaluation overview](template/docs/evaluation/README.md) | Execution model, CLI, file structure. |
| [Pipelines](template/docs/evaluation/pipelines.md) | YAML schema and 8-benchmark menu. |
| [Benchmarks](template/docs/evaluation/benchmarks.md) | Scoring behavior per benchmark. |
| [Datasets](template/docs/evaluation/datasets.md) | Case schema and generation. |
| [Outputs](template/docs/evaluation/outputs.md) | Result and status contracts. |
| [Troubleshooting](template/docs/evaluation/troubleshooting.md) | Judge-model gotchas. |

**Why a separate component?** NeMo Evaluator has a large transitive dependency tree that should not be imposed on the core CLI repo. This component runs in its own isolated `uv` environment. The core CLI detects it via `[tool.af-component]` in `pyproject.toml` and invokes it as a subprocess.

**What it does:** sends each test prompt to the agent's OpenAI-compatible endpoint (black-box), then scores the response. It ships **8 isolated benchmarks**&mdash;pick one per run via a pipeline YAML. Three are **judge-based** (LLM-as-judge: `answer_quality`, `safety_refusal`, `faithfulness`) and five are **judge-free** (deterministic: `answer_correctness`, `instruction_following`, `prompt_injection`, `pii_leakage`, `tool_grounding`).

## Repository layout

```
af-component-evaluation/
├── template/
│   ├── docs/evaluation/           # User docs (ship with rendered project)
│   └── [[ evaluation_app_name ]]/ # Rendered component (run.py, pipelines, datasets)
├── copier-module.yaml             # Component metadata for doc generator
├── copier.yml                     # Copier template config
├── Taskfile.yml                   # Root tasks (test, lint)
└── README.md                      # This file
```

## Development commands

From the repo root:

```bash
task install    # uv sync
task test       # pytest (non-integration)
task lint       # ruff + mypy + yamlfix
```

From `template/[[ evaluation_app_name ]]/` (after a local Copier render or direct work in the template folder):

```bash
task eval -- --endpoint ... --pipeline ... --dataset ...
task generate -- --agent-description "..." --n 10 --output user_datasets/cases.json
task summarize
task test-integration   # requires DATAROBOT_API_TOKEN + DATAROBOT_ENDPOINT
```

The eval engine (`EvalRunner`, benchmarks, normalization) lives in the `datarobot-genai[eval]` package. This repo provides thin CLI wrappers (`run.py`, `generate.py`, `summarize.py`), default pipelines, sample datasets, and documentation.

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
| Judge returns 400 on Bedrock models | NeMo sends both `temperature` and `top_p` | Use an Azure GPT judge in the pipeline YAML. |
| Wrong judge model name | LiteLLM `datarobot/` prefix used against the gateway | Use gateway catalog names (for example `azure/gpt-5-5-2026-04-23`). |
| Cases marked inconclusive on safety runs | Judge endpoint content-filtered the adversarial prompt | Expected behavior&mdash;see [Outputs](template/docs/evaluation/outputs.md). |
| `task eval` cannot reach agent | Agent not running or wrong port | Start the agent (`dr run dev`) and confirm `http://localhost:8842/v1`. |

Full troubleshooting guide: [template/docs/evaluation/troubleshooting.md](template/docs/evaluation/troubleshooting.md).

# Next steps and cross-links

- [Getting started](template/docs/evaluation/getting-started.md)&mdash;first evaluation run.
- [NAT vs. NeMo](template/docs/evaluation/nat-vs-nemo.md)&mdash;when to use batch output testing vs. NAT `/evaluate`.
- [Writing your own benchmark](template/docs/evaluation/writing-benchmarks.md)&mdash;custom BYOB scorers.
- [DataRobot App Framework documentation](https://af.datarobot.com)&mdash;component model and CLI.
- [NeMo Evaluator BYOB](https://github.com/NVIDIA-NeMo/evaluator)&mdash;underlying benchmark framework.

# Contributing, changelog, support, and legal

See [AUTHORS](AUTHORS) and [LICENSE](LICENSE) for authorship and licensing.

To contribute, fork the repository, make changes on a branch, and open a pull request. Ensure `task test` passes before submitting. See [CONTRIBUTING.md](.github/CONTRIBUTING.md) for guidelines.

For support, see [DataRobot help](https://docs.datarobot.com/en/docs/get-started/troubleshooting/general-help.html) or open an issue on GitHub.
