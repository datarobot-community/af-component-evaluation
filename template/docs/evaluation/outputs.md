# Outputs

Every evaluation run writes results to fixed paths under `output/`. The external CLI polls `eval_status.json` for progress and reads `eval_results.json` on completion.

## Run lifecycle

1. **Validate**&mdash;health-check the agent endpoint (any HTTP response = reachable), verify the pipeline YAML, benchmark module, and dataset exist. Exit 1 on failure.
2. **Status**: running&mdash;writes `output/eval_status.json`.
3. **Execute**&mdash;converts the dataset to BYOB JSONL and runs the BYOB runner in-process.
4. **Normalize**&mdash;reads `byob_results.json` (aggregate) and `byob_predictions.jsonl` (per-sample) from `output/raw/<run_id>/<benchmark_name>/`.
5. **Status**: complete&mdash;writes `output/eval_results.json` and updates the status file.

If any step fails, `eval_status.json` is set to `"failed"` with an error message.

**Exit codes**: `0` success · `1` validation error · `2` runner failed · `3` normalization failed.

## Fixed output contract

These paths never change&mdash;the external CLI always reads from here:

```
output/
├── eval_status.json     # Written at start and end of every run.
├── eval_results.json    # Written on success only.
└── raw/<run_id>/<benchmark_name>/
    ├── byob_results.json       # Raw BYOB aggregate.
    └── byob_predictions.jsonl  # Raw BYOB per-sample.
```

### `eval_status.json`

Schema: [`docs/evaluation/schemas/status_schema.json`](./schemas/status_schema.json).

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

### `eval_results.json`

Schema: [`docs/evaluation/schemas/output_schema.json`](./schemas/output_schema.json).

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

Rates (`mean_score`, `pass_rate`, and so on) are computed over **scored** cases only.

Every case carries a single normalized `score` (0–1), whatever the benchmark. For judge-based benchmarks `has_judge` is `true` and `judge_grade` holds the raw grade (for example `"5"`) for traceability. Judge-free benchmarks set `has_judge` to `false` and score deterministically. `reason` is the human-readable explanation in both cases.

## Inconclusive cases

A case is **inconclusive** when it cannot be fairly scored&mdash;most often when the **judge call itself fails** (for example, the judge endpoint applies input content filtering to an adversarial prompt&mdash;see [Troubleshooting](./troubleshooting.md)), or when a required dataset field is missing.

Inconclusive cases get `score: null` and `passed: null`, and are **excluded** from rates rather than counted as a `0.0` failure. The summary reports both `scored_cases` and `inconclusive_cases` so you can see how much of the run was actually graded.

## Viewing results

Pretty-print the latest results with `task summarize`:

```bash
task summarize
```

## See also

- [Getting started](./getting-started.md)&mdash;run an evaluation and read the output.
- [Benchmarks](./benchmarks.md)&mdash;how each benchmark produces scores.
- [Troubleshooting](./troubleshooting.md)&mdash;why cases may be marked inconclusive.
