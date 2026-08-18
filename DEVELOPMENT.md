# Developing `af-component-evaluation`

This document covers the internals of the component itself: how a run executes,
the output contract, and how to add benchmarks. It is for people working **on**
this repository.

If you are *using* the component in a project, you want the user-facing
documentation instead. It ships in [`template/docs/evaluation/`](template/docs/evaluation/)
and is rendered to `docs/evaluation/` in your project. Start at
[`template/docs/evaluation/README.md`](template/docs/evaluation/README.md).

**Why a separate component?** NeMo Evaluator has a large transitive dependency tree that should not be imposed on the core CLI repo. This component runs in its own isolated `uv` environment. The core CLI detects it via `[tool.af-component]` in `pyproject.toml` and invokes it as a subprocess&mdash;no imports, no shared dependencies.

## Running the test suite

```bash
task install      # set up the component environment
task test         # unit tests
task lint         # ruff + mypy
```

Install the pre-commit hooks once, so formatting and secret checks run on commit:

```bash
uvx pre-commit install
```

---

## How it actually runs (BYOB, in-process&mdash;no Docker)

A note on what this is **not**: it does *not* use `nemo-evaluator-launcher`. The launcher runs every task inside an `nvcr.io` Docker container (`--gpus all`) and only exposes fixed benchmarks (MMLU, GSM8K, MTBench, …)&mdash;there is no generic "custom Q&A + judge" task, and the Docker path does not run on a laptop.

This component uses NeMo's **BYOB** framework (`nemo_evaluator.contrib.byob`): a custom benchmark defined in plain Python, run **in-process** via the BYOB runner. Both the agent (target) and the judge are reached over plain OpenAI-compatible HTTP&mdash;there is **no LiteLLM layer** (see [Troubleshooting](template/docs/evaluation/troubleshooting.md) for why that matters for model names).

```
run.py
  ├─ validates endpoint / pipeline / dataset
  ├─ converts dataset JSON → BYOB JSONL
  ├─ reads user_pipelines/<name>.yaml (benchmark + optional judge + run params)
  └─ runs the BYOB runner in-process
         ├─ for each case: POST agent endpoint, get response
         ├─ scorer (datarobot_genai/eval/benchmarks/<name>.py) → judge call OR deterministic check → grade
         └─ writes byob_results.json (aggregate) + byob_predictions.jsonl (per-sample)
  └─ normalizes raw output → output/eval_results.json
```

---

## User workflow

1. **Add the component**&mdash;the core CLI detects it automatically via `[tool.af-component]` in `pyproject.toml`.

2. **Pick a pipeline**&mdash;choose one of the 8 defaults in `user_pipelines/` (you usually do not edit it; point `--dataset` at your data). Judge-based pipelines carry a `judge:` block; judge-free ones omit it:
   ```yaml
   benchmark:
     module: datarobot_genai/eval/benchmarks/answer_quality.py   # the BYOB benchmark
     name: answer_quality                              # normalized benchmark name
   target:
     model_type: chat
     model_id: unknown            # "unknown" -> the agent uses its own default LLM
     api_key_name: AGENT_API_KEY  # only sent if that env var is set (local agent needs none)
   judge:                         # OMIT this whole block for judge-free benchmarks
     url: https://app.datarobot.com/api/v2/genai/llmgw   # OpenAI-compatible; NeMo appends /chat/completions
     model_id: azure/gpt-5-5-2026-04-23   # gateway CATALOG name (NOT a litellm datarobot/ prefix)
     api_key_name: DATAROBOT_API_TOKEN
   run:
     parallelism: 4
     max_tokens: 1024
     temperature: 0.0
     timeout_per_sample: 180
   ```
   **Judge model names** are whatever the named endpoint expects. Against the DR LLM gateway directly that is the gateway catalog name (no `datarobot/` prefix)&mdash;for example, `azure/gpt-5-5-2026-04-23`. List models with `GET https://app.datarobot.com/api/v2/genai/llmgw/models`. ⚠️ Bedrock/Claude models cannot be used as the stock judge&mdash;see [Troubleshooting](template/docs/evaluation/troubleshooting.md).

3. **Add or select a dataset**&mdash;copy `user_datasets/sample_<benchmark>.json`, or generate cases with `generate.py`.

4. **Launch from the external CLI**&mdash;it presents pipelines/datasets, prompts for the agent endpoint, then invokes this component.

5. **View results**&mdash;read `output/eval_status.json` for status and `output/eval_results.json` for results.

---

## CLI interface

```bash
uv run python run.py \
  --endpoint  http://localhost:8842/v1 \                  # agent OpenAI-compatible endpoint
  --pipeline  answer_quality.yaml \                        # filename in user_pipelines/
  --dataset   user_datasets/sample_answer_quality.json     # optional, defaults to sample_answer_quality.json

# Validate inputs without running:
uv run python run.py --endpoint ... --pipeline ... --dry-run
```

**Environment variables**:

| Variable | Required | Description |
|---|---|---|
| `DATAROBOT_API_TOKEN` | yes | Bearer token for the DR LLM gateway (judge runs and `generate.py`). Set in `.env`. |
| `DATAROBOT_ENDPOINT` | yes | DataRobot endpoint URL (for example, `https://app.datarobot.com`). Set in `.env`. |
| `AGENT_API_KEY` | no | Bearer token for the agent endpoint. Only sent if set&mdash;a local DRUM agent needs none. |

The judge `url`/`model_id`/`api_key_name` come from the pipeline YAML; `run.py` exports them to the benchmark as `JUDGE_URL` / `JUDGE_MODEL_ID` / `JUDGE_API_KEY_NAME`.

---

## Run lifecycle

1. **Validate**&mdash;health-check the agent endpoint (any HTTP response = reachable), verify pipeline YAML + benchmark module + dataset exist. Exit 1 on failure.
2. **Status**: running&mdash;writes `output/eval_status.json`.
3. **Execute**&mdash;converts dataset to BYOB JSONL, runs the BYOB runner in-process.
4. **Normalize**&mdash;reads `byob_results.json` (aggregate) + `byob_predictions.jsonl` (per-sample) from `output/raw/<run_id>/<benchmark_name>/`.
5. **Status**: complete&mdash;writes `output/eval_results.json`, updates `output/eval_status.json`.

If any step fails, `eval_status.json` is set to `"failed"` with an error message. Exit codes: `0` success, `1` validation, `2` runner failed, `3` normalization failed.

### Inconclusive cases

If the agent answers but the **judge call itself fails** (for example, the judge endpoint applies input content filtering to an adversarial prompt&mdash;see [Troubleshooting](template/docs/evaluation/troubleshooting.md)), that case is marked **inconclusive**: `score: null`, `passed: null`, and it is **excluded** from rates rather than counted as a `0.0` failure. The summary reports `scored_cases` and `inconclusive_cases`.

---

## Fixed output contract

These paths never change&mdash;the external CLI always reads from here:

```
output/
├── eval_status.json     # written at start and end of every run
├── eval_results.json    # written on success only
└── raw/<run_id>/<benchmark_name>/
    ├── byob_results.json       # raw BYOB aggregate
    └── byob_predictions.jsonl  # raw BYOB per-sample
```

### `output/eval_status.json`&mdash;schema: `docs/evaluation/schemas/status_schema.json`

```json
{
  "status": "complete",
  "run_id": "20260601_100054",
  "updated_at": "2026-06-01T14:00:54Z",
  "pipeline": "answer_quality.yaml",
  "agent_endpoint": "http://localhost:8842/v1",
  "error": null
}
```

`status` values: `running` → `complete` | `failed`

### `output/eval_results.json`&mdash;schema: `docs/evaluation/schemas/output_schema.json`

```json
{
  "run_id": "20260601_100054",
  "completed_at": "2026-06-01T14:00:54Z",
  "agent_endpoint": "http://localhost:8842/v1",
  "pipeline": "answer_quality.yaml",
  "total_cases": 6,
  "summary": {
    "scored_cases": 5,
    "inconclusive_cases": 1,
    "mean_score": 0.92,
    "pass_rate": 1.0,
    "good_case_pass_rate": 1.0,
    "bad_case_pass_rate": 1.0,
    "nemo_aggregate": {
      "answer_quality.pass@1.score": 0.92,
      "answer_quality.pass@1.quality": 0.8667
    }
  },
  "cases": [
    {
      "id": "good-002",
      "input": "Explain the differences between RAG and fine-tuning",
      "expected_behavior": "good",
      "agent_response": "...",
      "benchmark": "answer_quality",
      "has_judge": true,
      "score": 1.0,
      "passed": true,
      "reason": "judge grade: 5",
      "judge_grade": "5",
      "notes": "...",
      "source": "collected"
    }
  ]
}
```

Rates (`mean_score`, `pass_rate`, …) are computed over **scored** cases only.

---

## Core CLI detection pattern

The core CLI discovers this component by scanning for `pyproject.toml` files with `[tool.af-component]`:

```python
import tomllib
from pathlib import Path

for pyproject in Path(".").rglob("pyproject.toml"):
    data = tomllib.loads(pyproject.read_text())
    meta = data.get("tool", {}).get("af-component", {})
    if meta.get("type") == "evaluation":
        component_dir  = pyproject.parent
        entrypoint     = component_dir / meta["entrypoint"]       # run.py
        pipelines_dir  = component_dir / meta["pipelines_dir"]    # user_pipelines/
        datasets_dir   = component_dir / meta["datasets_dir"]     # user_datasets/
        status_path    = component_dir / meta["output_status"]    # output/eval_status.json
        results_path   = component_dir / meta["output_results"]   # output/eval_results.json
        # Invoke:
        # uv run --project <component_dir> python <entrypoint> \
        #   --endpoint <url> --pipeline <file> --dataset <file>
```

---

## Directory structure

This is the layout a user gets **after** rendering, not the layout of this
repository. In the repo these files live under
`template/[[ evaluation_app_name ]]/`, and the docs under `template/docs/`.

```
<your-project>/
│
├── docs/evaluation/               # User-facing docs   (repo: template/docs/)
│   ├── README.md                  # Docs index
│   ├── benchmarks.md              # The 8 benchmarks
│   ├── pipelines.md               # Pipeline YAML reference
│   ├── ...
│   └── schemas/                   # JSON contracts — stable API surface
│       ├── input_schema.json      # CLI flags: --endpoint, --pipeline, --dataset
│       ├── dataset_schema.json    # Test case dataset format
│       ├── status_schema.json     # output/eval_status.json format
│       └── output_schema.json     # output/eval_results.json format
│
└── evaluations/                   # The component  (repo: template/[[ evaluation_app_name ]]/)
    │                              # Directory name is chosen by the copier wizard.
    │
    ├── user_pipelines/            # Pipeline YAML — benchmark/target/[judge]/run
    │   ├── README.md              # Pipeline format docs + the 8-benchmark menu
    │   ├── <8 default>.yaml       # answer_quality, safety_refusal, faithfulness (judge);
    │   │                          # answer_correctness, instruction_following,
    │   │                          # prompt_injection, pii_leakage, tool_grounding (judge-free)
    │   └── user_example_*.py      # Annotated templates for writing your own
    │
    ├── user_datasets/             # Test case datasets (committed, human-reviewed)
    │   └── sample_<benchmark>.*   # One starter dataset per benchmark (.json / .csv)
    │
    ├── output/                    # Runtime output — gitignored
    │   ├── eval_status.json       # ← external CLI polls this
    │   ├── eval_results.json      # ← external CLI reads this on completion
    │   └── raw/<run_id>/<benchmark>/   # Raw BYOB output
    │
    ├── tests/                     # Component tests
    ├── run.py                     # Thin wrapper → datarobot_genai.eval.cli.run_main
    ├── generate.py                # Thin wrapper → datarobot_genai.eval.cli.generate_main
    ├── summarize.py               # Thin wrapper → datarobot_genai.eval.cli.summarize_main
    ├── Taskfile.yml               # task install / test / lint / run
    └── pyproject.toml             # uv environment + [tool.af-component] detection marker
```

The eval engine and the 8 BYOB benchmark modules are **not** in this tree. They
ship in the `datarobot-genai[eval]` package under
`datarobot_genai/eval/benchmarks/`.

---

## Adding a new benchmark / pipeline

A benchmark is a Python module using `nemo_evaluator.contrib.byob` (`@benchmark` + `@scorer`). The scorer can use NeMo's built-in judge templates (`binary_qa`, `binary_qa_partial`, `likert_5`, `safety`) via `judge_score`, or score deterministically with no judge at all. The 8 built-ins live in the `datarobot-genai[eval]` package (`datarobot_genai/eval/benchmarks/`) and make good references; to author your own, copy one of the annotated `user_example_benchmark_*.py` templates in `user_pipelines/`.

```bash
cp user_pipelines/user_example_benchmark_judge_based.py user_pipelines/my_benchmark.py
cp user_pipelines/answer_quality.yaml user_pipelines/my_pipeline.yaml
# point benchmark.module/name at your benchmark; set or remove the judge block
uv run python run.py --endpoint ... --pipeline my_pipeline.yaml --dataset ...
```

## Generating test cases

```bash
uv run python generate.py \
  --agent-description "A research assistant that answers questions concisely" \
  --n 20 \
  --output user_datasets/my_agent_cases.json
# Review and edit, then commit as ground truth
```

## Viewing results

```bash
uv run python summarize.py output/
```
