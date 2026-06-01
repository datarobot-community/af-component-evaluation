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
</p>


Batch evaluation component for DataRobot agents using the [NeMo Evaluator](https://github.com/NVIDIA-NeMo/evaluator) **BYOB** (Bring Your Own Benchmark) framework.

**Why a separate component?** NeMo Evaluator's dependency tree is heavy and carries CVEs that should not infect the core CLI repo. This component runs in its own isolated `uv` environment. The core CLI detects it via `[tool.af-component]` in `pyproject.toml` and invokes it as a subprocess — no imports, no shared dependencies.

**What it does:** sends each test prompt to the agent's OpenAI-compatible endpoint (black-box), then scores the agent's response with an **LLM-as-judge**. Good cases are scored for quality (1–5 Likert → 0–1); bad cases are scored for safety (SAFE/UNSAFE). Output is normalized to a stable JSON schema.

---

## How it actually runs (BYOB, in-process — no Docker)

A note on what this is **not**: it does *not* use `nemo-evaluator-launcher`. The launcher runs every task inside an `nvcr.io` Docker container (`--gpus all`) and only exposes fixed benchmarks (MMLU, GSM8K, MTBench, …) — there is no generic "custom Q&A + judge" task, and the Docker path won't run on a laptop.

Instead we use NeMo's **BYOB** framework (`nemo_evaluator.contrib.byob`): a custom benchmark defined in plain Python, run **in-process** via the BYOB runner. Both the agent (target) and the judge are reached over plain OpenAI-compatible HTTP — there is **no LiteLLM layer** (see `the known issues notes` for why that matters for model names).

```
run_eval.py
  ├─ validates endpoint / pipeline / dataset
  ├─ converts dataset JSON → BYOB JSONL
  ├─ reads pipelines/<name>.yaml (benchmark + judge + run params)
  └─ subprocess: python -m nemo_evaluator.contrib.byob.runner
         ├─ for each case: POST agent endpoint, get response
         ├─ scorer (benchmarks/<name>.py) → LLM judge call → grade
         └─ writes byob_results.json (aggregate) + byob_predictions.jsonl (per-sample)
  └─ normalizes raw output → output/eval_results.json
```

---

## User Workflow

1. **Add the component** — the core CLI detects it automatically via `[tool.af-component]` in `pyproject.toml`.

2. **Configure a pipeline** — edit a YAML in `pipelines/`. This is the main file you touch to change evaluation behavior:
   ```yaml
   benchmark:
     module: benchmarks/agent_quality_safety.py   # the BYOB benchmark
     name: agent_quality_safety                    # normalized benchmark name
   target:
     model_type: chat
     model_id: unknown            # "unknown" -> the agent uses its own default LLM
     api_key_name: AGENT_API_KEY  # only sent if that env var is set (local agent needs none)
   judge:
     url: https://app.datarobot.com/api/v2/genai/llmgw   # OpenAI-compatible; NeMo appends /chat/completions
     model_id: azure/gpt-4o-2024-11-20   # gateway CATALOG name (NOT a litellm datarobot/ prefix)
     api_key_name: DATAROBOT_API_TOKEN
   run:
     parallelism: 4
     max_tokens: 1024
     temperature: 0.0
     timeout_per_sample: 180
   ```
   **Judge model names** are whatever the named endpoint expects. Against the DR LLM gateway directly that's the gateway catalog name (no `datarobot/` prefix) — e.g. `azure/gpt-4o-2024-11-20`. List models with `GET https://app.datarobot.com/api/v2/genai/llmgw/models`. ⚠️ Bedrock/Claude models can't be used as the stock judge — see `the known issues notes #1`.

3. **Add or select a dataset** — drop a JSON file in `datasets/` following `datasets/schema.md`, or generate cases with `generate/generate_test_cases.py`.

4. **Launch from the external CLI** — it presents pipelines/datasets, prompts for the agent endpoint, then invokes this component.

5. **View results** — read `output/eval_status.json` for status and `output/eval_results.json` for results.

---

## CLI Interface

```bash
uv run python run_eval.py \
  --endpoint  http://localhost:8842/v1 \      # agent OpenAI-compatible endpoint
  --pipeline  agent_quality_safety.yaml \      # filename in pipelines/
  --dataset   datasets/sample_cases.json       # optional, defaults to sample_cases.json

# Validate inputs without running:
uv run python run_eval.py --endpoint ... --pipeline ... --dry-run
```

**Environment variables:**

| Variable | Required | Description |
|---|---|---|
| `DATAROBOT_API_TOKEN` | yes | Bearer token for the judge (DR LLM gateway). Set in `.env`. |
| `AGENT_API_KEY` | no | Bearer token for the agent endpoint. Only sent if set — a local DRUM agent needs none. |

The judge `url`/`model_id`/`api_key_name` come from the pipeline YAML; `run_eval.py` exports them to the benchmark as `JUDGE_URL` / `JUDGE_MODEL_ID` / `JUDGE_API_KEY_NAME`.

---

## Run Lifecycle

1. **Validate** — health-check the agent endpoint (any HTTP response = reachable), verify pipeline YAML + benchmark module + dataset exist. Exit 1 on failure.
2. **Status: running** — writes `output/eval_status.json`.
3. **Execute** — converts dataset to BYOB JSONL, runs the BYOB runner in-process as a subprocess.
4. **Normalize** — reads `byob_results.json` (aggregate) + `byob_predictions.jsonl` (per-sample) from `output/raw/<run_id>/<benchmark_name>/`.
5. **Status: complete** — writes `output/eval_results.json`, updates `output/eval_status.json`.

If any step fails, `eval_status.json` is set to `"failed"` with an error message. Exit codes: `0` success, `1` validation, `2` runner failed, `3` normalization failed.

### Inconclusive cases

If the agent answers but the **judge call itself fails** (e.g. the gateway content-filters an adversarial prompt — see `the known issues notes #3`), that case is marked **inconclusive**: `quality_score: null`, `passed: null`, and it is **excluded** from rates rather than counted as a `0.0` failure. The summary reports `scored_cases` and `inconclusive_cases`.

---

## Fixed Output Contract

These paths never change — the external CLI always reads from here:

```
output/
├── eval_status.json     # written at start and end of every run
├── eval_results.json    # written on success only
└── raw/<run_id>/<benchmark_name>/
    ├── byob_results.json       # raw BYOB aggregate
    └── byob_predictions.jsonl  # raw BYOB per-sample
```

### `output/eval_status.json` — schema: `schemas/status_schema.json`

```json
{
  "status": "complete",
  "run_id": "20260601_100054",
  "updated_at": "2026-06-01T14:00:54Z",
  "pipeline": "agent_quality_safety.yaml",
  "agent_endpoint": "http://localhost:8842/v1",
  "error": null
}
```

`status` values: `running` → `complete` | `failed`

### `output/eval_results.json` — schema: `schemas/output_schema.json`

```json
{
  "run_id": "20260601_100054",
  "completed_at": "2026-06-01T14:00:54Z",
  "agent_endpoint": "http://localhost:8842/v1",
  "pipeline": "agent_quality_safety.yaml",
  "total_cases": 6,
  "summary": {
    "scored_cases": 5,
    "inconclusive_cases": 1,
    "mean_quality_score": 0.92,
    "pass_rate": 1.0,
    "good_case_pass_rate": 1.0,
    "bad_case_pass_rate": 1.0,
    "nemo_aggregate": {
      "agent_quality_safety.pass@1.score": 0.92,
      "agent_quality_safety.pass@1.quality": 0.8667,
      "agent_quality_safety.pass@1.safety": 1.0
    }
  },
  "cases": [
    {
      "id": "good-002",
      "input": "Explain the differences between RAG and fine-tuning",
      "expected_behavior": "good",
      "agent_response": "...",
      "quality_score": 1.0,
      "judge_reason": "judge grade: 5",
      "passed": true,
      "answer_match_score": null,
      "notes": "...",
      "source": "collected"
    }
  ]
}
```

Rates (`mean_quality_score`, `pass_rate`, …) are computed over **scored** cases only.

---

## Core CLI Detection Pattern

The core CLI discovers this component by scanning for `pyproject.toml` files with `[tool.af-component]`:

```python
import tomllib
from pathlib import Path

for pyproject in Path(".").rglob("pyproject.toml"):
    data = tomllib.loads(pyproject.read_text())
    meta = data.get("tool", {}).get("af-component", {})
    if meta.get("type") == "evaluation":
        component_dir  = pyproject.parent
        entrypoint     = component_dir / meta["entrypoint"]       # run_eval.py
        pipelines_dir  = component_dir / meta["pipelines_dir"]    # pipelines/
        datasets_dir   = component_dir / meta["datasets_dir"]     # datasets/
        status_path    = component_dir / meta["output_status"]    # output/eval_status.json
        results_path   = component_dir / meta["output_results"]   # output/eval_results.json
        # Invoke:
        # uv run --project <component_dir> python <entrypoint> \
        #   --endpoint <url> --pipeline <file> --dataset <file>
```

---

## Directory Structure

```
af-component-evaluation/
│
├── schemas/                       # JSON contracts — stable API surface
│   ├── input_schema.json          # CLI flags: --endpoint, --pipeline, --dataset
│   ├── status_schema.json         # output/eval_status.json format
│   └── output_schema.json         # output/eval_results.json format
│
├── pipelines/                     # Pipeline YAML — our simple schema (benchmark/target/judge/run)
│   ├── README.md                  # pipeline format docs
│   └── agent_quality_safety.yaml  # the default LLM-as-judge pipeline
│
├── benchmarks/                    # NeMo BYOB benchmark definitions (Python)
│   └── agent_quality_safety.py    # good -> likert_5 quality, bad -> safety; LLM judge
│
├── datasets/                      # Test case datasets (committed, human-reviewed)
│   ├── sample_cases.json          # Default — 6 starter cases (good + bad)
│   └── schema.md                  # Dataset field documentation
│
├── generate/
│   └── generate_test_cases.py     # Claude-powered synthetic test case generator
│
├── output/                        # Runtime output — gitignored
│   ├── eval_status.json           # ← external CLI polls this
│   ├── eval_results.json          # ← external CLI reads this on completion
│   └── raw/<run_id>/<benchmark>/  # Raw BYOB output (byob_results.json, byob_predictions.jsonl)
│
├── scripts/
│   └── summarize_results.py       # Human-readable pretty-print of eval_results.json
│
├── docs/
│   └── nat-eval-vs-nemo-evaluator.md  # Explanation of the two evaluation systems
│
├── the known issues notes                        # Known issues / gotchas (Bedrock judge, LiteLLM, content filter)
├── run_eval.py                    # Main CLI entrypoint
└── pyproject.toml                 # uv environment + [tool.af-component] detection marker
```

---

## Adding a New Benchmark / Pipeline

A benchmark is a Python module using `nemo_evaluator.contrib.byob` (`@benchmark` + `@scorer`). The scorer can use NeMo's built-in judge templates (`binary_qa`, `binary_qa_partial`, `likert_5`, `safety`) via `judge_score`, or any custom logic. See `benchmarks/agent_quality_safety.py` for a working example.

```bash
cp pipelines/agent_quality_safety.yaml pipelines/my_pipeline.yaml
# point benchmark.module/name at your benchmark; set judge.model_id
uv run python run_eval.py --endpoint ... --pipeline my_pipeline.yaml
```

## Generating Test Cases

```bash
uv run python generate/generate_test_cases.py \
  --agent-description "A research assistant that answers questions concisely" \
  --n 20 \
  --output datasets/my_agent_cases.json
# Review and edit, then commit as ground truth
```

## Viewing Results

```bash
uv run python scripts/summarize_results.py output/
```

## Distinction from NAT /evaluate

See `docs/nat-eval-vs-nemo-evaluator.md`. In brief:

| | This component | NAT `/evaluate` |
|---|---|---|
| **Tests** | Agent output quality at scale | Agent trajectory and reasoning |
| **Perspective** | Black-box — sees only the final response | Inside-out — sees tool calls and intermediate steps |
| **Trigger** | CLI subprocess | `POST /evaluate` on running NAT server |
| **Use when** | Batch regression testing, safety checks, release gates | Playground / development, checking agent reasoning |
