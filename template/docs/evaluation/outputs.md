# Outputs

## Run lifecycle

1. **Validate** — health-check the agent endpoint (any HTTP response = reachable),
   verify the pipeline YAML + benchmark module + dataset exist. Exit 1 on failure.
2. **Status: running** — writes `output/eval_status.json`.
3. **Execute** — converts the dataset to BYOB JSONL, runs the BYOB runner in-process.
4. **Normalize** — reads `byob_results.json` (aggregate) + `byob_predictions.jsonl`
   (per-sample) from `output/raw/<run_id>/<benchmark_name>/`.
5. **Status: complete** — writes `output/eval_results.json`, updates the status file.

If any step fails, `eval_status.json` is set to `"failed"` with an error message.

**Exit codes:** `0` success · `1` validation error · `2` runner failed ·
`3` normalization failed.

## Fixed output contract

These paths never change — the external CLI always reads from here:

```
output/
├── eval_status.json     # written at start and end of every run
├── eval_results.json    # written on success only
└── raw/<run_id>/<benchmark_name>/
    ├── byob_results.json       # raw BYOB aggregate
    └── byob_predictions.jsonl  # raw BYOB per-sample
```

### `eval_status.json` — schema: `docs/evaluation/schemas/status_schema.json`

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

`status` transitions: `running` → `complete` | `failed`.

### `eval_results.json` — schema: `docs/evaluation/schemas/output_schema.json`

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
      "benchmark": "answer_quality",
      "input": "Explain the differences between RAG and fine-tuning",
      "expected_behavior": "good",
      "agent_response": "...",
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

Every case carries a single normalized `score` (0-1), whatever the benchmark. For
judge-based benchmarks `has_judge` is `true` and `judge_grade` holds the raw grade
(e.g. `"5"`) for traceability; judge-free benchmarks set `has_judge` to `false`
and score deterministically. `reason` is the human-readable explanation in both
cases.

## Inconclusive cases

A case is **inconclusive** when it can't be fairly scored — most often when the
**judge call itself fails** (e.g. the judge endpoint applies input content
filtering to an adversarial prompt — see [Troubleshooting](./troubleshooting.md)),
or when a required dataset field is missing.

Inconclusive cases get `score: null` and `passed: null`, and are
**excluded** from rates rather than counted as a `0.0` failure. The summary
reports both `scored_cases` and `inconclusive_cases` so you can see how much of
the run was actually graded.

## Viewing results

```bash
task summarize          # pretty-prints output/eval_results.json
```
