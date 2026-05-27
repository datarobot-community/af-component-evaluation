# af-component-evaluation

Batch evaluation component for DataRobot agents using the [NeMo Evaluator](https://github.com/NVIDIA-NeMo/evaluator).

**Why a separate component?** NeMo Evaluator's dependency tree is heavy and carries CVEs that should not infect the core CLI repo. This component runs in its own isolated `uv` environment. The core CLI detects it via `[tool.af-component]` in `pyproject.toml` and invokes it as a subprocess — no imports, no shared dependencies.

---

## User Workflow

1. **Add the component** — the core CLI detects it automatically via `[tool.af-component]` in `pyproject.toml`.

2. **Configure a pipeline** — edit a YAML in `pipelines/`. This is the only file you need to touch to change evaluation behavior. Set the judge LLM using a LiteLLM model name (same convention NAT uses everywhere):
   ```yaml
   judge:
     model: "openai/gpt-4o-mini"      # LiteLLM model name
     api_key: OPENAI_API_KEY           # env var name holding the key
   ```
   Available model name formats: `openai/gpt-4o-mini`, `anthropic/claude-haiku-4-5-20251001`, `nvidia_nim/meta/llama-3.1-70b-instruct`, `azure/gpt-4o`, etc.

3. **Add or select a dataset** — drop a JSON file in `datasets/` following the schema in `datasets/schema.md`, or generate cases synthetically with `generate/generate_test_cases.py`.

4. **Launch from the external CLI** — the CLI presents available pipelines and datasets, prompts for the agent endpoint, then invokes this component.

5. **View results** — the external CLI reads `output/eval_status.json` for status and `output/eval_results.json` for results.

---

## CLI Interface

```bash
uv run python run_eval.py \
  --endpoint  http://localhost:8080/v1 \   # agent OpenAI-compatible endpoint
  --pipeline  custom_qa_judge.yaml    \   # filename in pipelines/
  --dataset   datasets/sample_cases.json  # optional, defaults to sample_cases.json

# Validate inputs without running:
uv run python run_eval.py --endpoint ... --pipeline ... --dry-run
```

**Environment variables** — present automatically at execution time, no manual export needed in normal use:

| Variable | Required | Description |
|---|---|---|
| `AGENT_API_KEY` | yes | API key for the agent endpoint |
| `AGENT_MODEL_NAME` | yes | LiteLLM model name the agent endpoint expects |
| `LITELLM_PROXY_URL` | yes | LiteLLM proxy URL — routes all LLM calls including the judge |
| `<JUDGE_API_KEY_VAR>` | yes | Whichever env var your judge model's API key lives in (set in pipeline YAML) |
| `MAX_CONCURRENCY` | no | Parallel requests to the agent (default: 4) |

---

## Run Lifecycle

1. **Validate** — health-check the agent endpoint, verify pipeline YAML exists, verify dataset exists. Exit 1 on any failure.
2. **Status: running** — writes `output/eval_status.json`
3. **Execute** — converts dataset to NeMo OpenAI JSONL, renders pipeline YAML with runtime substitutions, runs `nemo-evaluator-launcher` subprocess
4. **Normalize** — parses NeMo's `artifacts/results.json` (aggregate) + `artifacts/report.json` (per-sample scores)
5. **Status: complete** — writes `output/eval_results.json`, updates `output/eval_status.json`

If any step fails, `eval_status.json` is set to `"failed"` with an error message.

---

## Fixed Output Contract

These paths never change — the external CLI always reads from here:

```
output/
├── eval_status.json     # written at start and end of every run
└── eval_results.json    # written on success only
```

### `output/eval_status.json` — schema: `schemas/status_schema.json`

```json
{
  "status": "complete",
  "run_id": "20250526_143022",
  "updated_at": "2025-05-26T14:30:45Z",
  "pipeline": "custom_qa_judge.yaml",
  "agent_endpoint": "http://localhost:8080/v1",
  "error": null
}
```

`status` values: `running` → `complete` | `failed`

### `output/eval_results.json` — schema: `schemas/output_schema.json`

```json
{
  "run_id": "20250526_143022",
  "completed_at": "2025-05-26T14:30:45Z",
  "agent_endpoint": "http://localhost:8080/v1",
  "pipeline": "custom_qa_judge.yaml",
  "total_cases": 6,
  "summary": {
    "mean_quality_score": 0.82,
    "pass_rate": 0.83,
    "good_case_pass_rate": 1.0,
    "bad_case_pass_rate": 0.67,
    "nemo_aggregate": {}
  },
  "cases": [
    {
      "id": "good-001",
      "input": "What are the top AI trends...",
      "expected_behavior": "good",
      "agent_response": "...",
      "quality_score": 0.95,
      "judge_reason": "Response was accurate and well-sourced.",
      "passed": true,
      "answer_match_score": null,
      "notes": "...",
      "source": "collected"
    }
  ]
}
```

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
├── schemas/                      # JSON contracts — stable API surface
│   ├── input_schema.json         # CLI flags: --endpoint, --pipeline, --dataset
│   ├── status_schema.json        # output/eval_status.json format
│   └── output_schema.json        # output/eval_results.json format
│
├── pipelines/                    # NeMo Evaluator YAML — NeMo's native Hydra format
│   ├── README.md                 # NeMo schema docs, LiteLLM model name convention
│   └── custom_qa_judge.yaml      # LLM-as-judge pipeline — configure judge.model here
│
├── datasets/                     # Test case datasets (committed, human-reviewed)
│   ├── sample_cases.json         # Default — 6 starter cases (good + bad)
│   └── schema.md                 # Dataset field documentation
│
├── generate/
│   └── generate_test_cases.py    # Claude-powered synthetic test case generator
│
├── output/                       # Runtime output — gitignored
│   ├── eval_status.json          # ← external CLI polls this
│   ├── eval_results.json         # ← external CLI reads this on completion
│   └── raw/<run_id>/artifacts/   # Raw NeMo output (results.json, report.json)
│
├── scripts/
│   └── summarize_results.py      # Human-readable pretty-print of eval_results.json
│
├── docs/
│   └── nat-eval-vs-nemo-evaluator.md  # Explanation of the two evaluation systems
│
├── run_eval.py                   # Main CLI entrypoint
└── pyproject.toml                # uv environment + [tool.af-component] detection marker
```

---

## Adding a New Pipeline

```bash
cp pipelines/custom_qa_judge.yaml pipelines/my_pipeline.yaml
# Edit my_pipeline.yaml — set judge.model to a LiteLLM model name
uv run python run_eval.py --endpoint ... --pipeline my_pipeline.yaml
```

See `pipelines/README.md` for NeMo's Hydra YAML format and LiteLLM model name examples.

## Generating Test Cases

```bash
uv run python generate/generate_test_cases.py \
  --agent-description "A content planner and writer that researches topics" \
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
