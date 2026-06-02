# Evaluation

The evaluation component runs **batch, black-box evaluations** of a DataRobot
agent: it sends each test prompt to the agent's OpenAI-compatible endpoint, then
scores the response. It is built on the [NeMo Evaluator](https://github.com/NVIDIA-NeMo/evaluator)
**BYOB** (Bring Your Own Benchmark) framework and ships **8 isolated benchmarks**
covering quality, safety, correctness, and security.

It runs as its own isolated `uv` environment and is discovered by the core CLI
via `[tool.af-component]` in `pyproject.toml` — no shared imports, no shared
dependencies. The core CLI invokes it as a subprocess.

> All docs for this component live in `docs/evaluation/` regardless of what the
> component folder is named. Commands shown below run from inside the component
> directory (the folder named during setup, e.g. `evaluations/`).

| Section | Description |
|---|---|
| [How it runs](#how-it-runs-byob-in-process) | The BYOB, in-process execution model (no Docker, no GPUs). |
| [Quick start](#quick-start) | Pick a pipeline, point it at a dataset, run. |
| [File structure](#file-structure) | Where everything lives in the component. |
| [CLI interface](#cli-interface) | `run.py` flags and environment variables. |
| [Pipelines](./pipelines.md) | Pipeline YAML format and the 8-benchmark menu. |
| [Benchmarks](./benchmarks.md) | What each built-in benchmark measures and how it scores. |
| [Datasets](./datasets.md) | Dataset schema, per-benchmark fields, generating cases. |
| [Writing your own](./writing-benchmarks.md) | Author a custom benchmark + pipeline. |
| [Outputs](./outputs.md) | Run lifecycle, output contract, result/status schemas. |
| [NAT vs. NeMo](./nat-vs-nemo.md) | When to use this component vs. NAT `/evaluate`. |
| [Troubleshooting](./troubleshooting.md) | Judge-model gotchas and known limitations. |

## How it runs (BYOB, in-process)

This component does **not** use `nemo-evaluator-launcher`. The launcher runs every
task inside an `nvcr.io` Docker container (`--gpus all`) and only exposes fixed
academic benchmarks (MMLU, GSM8K, MTBench, …) — there is no generic
"custom Q&A + judge" task, and the Docker path won't run on a laptop.

Instead it uses NeMo's **BYOB** framework (`nemo_evaluator.contrib.byob`): a custom
benchmark defined in plain Python, run **in-process**. Both the agent (target) and
the judge are reached over plain OpenAI-compatible HTTP — there is **no LiteLLM
layer** (this matters for model names — see [Troubleshooting](./troubleshooting.md)).

```
run.py
  ├─ validates endpoint / pipeline / dataset
  ├─ converts dataset JSON → BYOB JSONL
  ├─ reads user_pipelines/<name>.yaml (benchmark + optional judge + run params)
  └─ runs the BYOB runner in-process
         ├─ for each case: POST agent endpoint, get response
         ├─ scorer (evaluator/benchmarks/<name>.py) → judge call OR deterministic check → grade
         └─ writes byob_results.json (aggregate) + byob_predictions.jsonl (per-sample)
  └─ normalizes raw output → output/eval_results.json
```

Each run uses **one** benchmark, selected by the pipeline YAML. Benchmarks are
either **judge-based** (an LLM grades the response) or **judge-free**
(deterministic checks, no judge model or credentials needed). See
[Benchmarks](./benchmarks.md).

## Quick start

```bash
# From the component directory:
task eval -- \
  --endpoint http://localhost:8842/v1 \
  --pipeline answer_quality.yaml \
  --dataset  user_datasets/sample_answer_quality.json

# Validate inputs without running:
task eval -- --endpoint ... --pipeline ... --dry-run

# Pretty-print the latest results:
task summarize
```

1. **Pick a pipeline** — choose one of the 8 defaults in `user_pipelines/`. You
   usually don't edit it; just point `--dataset` at your data. See [Pipelines](./pipelines.md).
2. **Pick or build a dataset** — copy `user_datasets/sample_<benchmark>.json`, or
   generate cases with `task generate`. See [Datasets](./datasets.md).
3. **Run** — from the external CLI, or directly with `task eval` / `uv run python run.py`.
4. **Read results** — `output/eval_status.json` (status) and `output/eval_results.json`
   (results). See [Outputs](./outputs.md).

## File structure

```
<component>/
├── run.py                      # Main entrypoint (the af-component detection target)
├── generate.py                 # Claude-powered synthetic test-case generator
├── summarize.py                # Pretty-print eval_results.json
├── Taskfile.yml                # task eval / generate / summarize / test / lint
├── pyproject.toml              # uv environment + [tool.af-component] marker
│
├── evaluator/                  # The eval engine (not meant to be edited)
│   ├── eval.py                 # EvalRunner: validate → run → normalize
│   ├── runner.py / generator.py / dataset.py / summarize.py / ...
│   ├── schemas/                # JSON contracts (input / status / output)
│   └── benchmarks/             # The 8 built-in BYOB benchmark modules
│       └── <benchmark>.py
│
├── user_pipelines/             # Pipeline YAML you select/edit
│   ├── <8 default pipelines>.yaml
│   ├── user_example_*.py       # Copy-me templates for custom benchmarks
│   └── user_example_*.yaml     # Copy-me templates for custom pipelines
│
├── user_datasets/              # Test-case datasets (committed, human-reviewed)
│   └── sample_<benchmark>.json
│
└── output/                     # Runtime output (gitignored)
    ├── eval_status.json        # ← external CLI polls this
    ├── eval_results.json       # ← external CLI reads this on completion
    └── raw/<run_id>/<benchmark>/   # raw BYOB output
```

## CLI interface

```bash
uv run python run.py \
  --endpoint  http://localhost:8842/v1 \    # agent OpenAI-compatible endpoint
  --pipeline  answer_quality.yaml \          # filename in user_pipelines/
  --dataset   user_datasets/sample_answer_quality.json   # optional
```

| Flag | Required | Description |
|---|:---:|---|
| `--endpoint` | yes | Base URL of the agent's OpenAI-compatible API. |
| `--pipeline` | yes | Pipeline YAML filename in `user_pipelines/`. |
| `--dataset` | no | Path to a test-case JSON file (defaults to `user_datasets/sample_answer_quality.json`). |
| `--dry-run` | no | Validate inputs and print what would run, without executing. |

**Environment variables:**

| Variable | Required | Description |
|---|:---:|---|
| `DATAROBOT_API_TOKEN` | judge runs only | Bearer token for the judge (DR LLM gateway). Set in `.env`. |
| `AGENT_API_KEY` | no | Bearer token for the agent endpoint. Only sent if set — a local DRUM agent needs none. |

The judge `url` / `model_id` / `api_key_name` come from the pipeline YAML;
`run.py` exports them to the benchmark as `JUDGE_URL` / `JUDGE_MODEL_ID` /
`JUDGE_API_KEY_NAME`. Judge-free pipelines need no judge credentials.

## Core CLI detection

The core CLI discovers this component by scanning for `pyproject.toml` files with
a `[tool.af-component]` table of `type = "evaluation"`:

```python
import tomllib
from pathlib import Path

for pyproject in Path(".").rglob("pyproject.toml"):
    meta = tomllib.loads(pyproject.read_text()).get("tool", {}).get("af-component", {})
    if meta.get("type") == "evaluation":
        component_dir = pyproject.parent
        entrypoint    = component_dir / meta["entrypoint"]      # run.py
        # Invoke: uv run --project <component_dir> python <entrypoint> \
        #           --endpoint <url> --pipeline <file> --dataset <file>
```

The marker also records `pipelines_dir`, `datasets_dir`, `output_status`, and
`output_results` so the CLI can list options and locate results.
