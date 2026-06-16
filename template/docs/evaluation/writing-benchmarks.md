# Writing your own benchmark

The 8 built-in benchmarks cover common cases, but you will often want to score
something specific to your agent. A benchmark is just a Python module using NeMo's
BYOB decorators — copy a template, rename it, and adapt the scoring logic.

Two annotated starter templates live in `user_pipelines/`:

| Files | Pattern | When to use |
|---|---|---|
| `user_example_benchmark_judge_free.py` + `user_example_pipeline_judge_free.yaml` | **Judge-free** | Deterministic pass/fail criteria — no LLM, always reproducible |
| `user_example_benchmark_judge_based.py` + `user_example_pipeline_judge_based.yaml` | **Judge-based** | A language model evaluates qualitative criteria |

**Steps:**

1. Copy the pair that fits your use case and rename both files.
2. Update `benchmark.module` and `benchmark.name` in the YAML to match.
3. Adjust the scoring logic in the `.py` (and the `judge:` block, or remove it).
4. Run it: `task eval -- --endpoint ... --pipeline my_pipeline.yaml --dataset ...`

Prefer **judge-free** whenever you have deterministic success criteria — it needs
no credentials and is fully reproducible.

## The mechanics

### `@benchmark(...)`

Declares the file as a NeMo BYOB benchmark.

```python
@benchmark(
    name="keyword_presence",   # MUST match benchmark.name in your pipeline YAML
    dataset="cases.jsonl",     # placeholder — the real file comes from --dataset at runtime
    prompt="{input}",          # the string SENT to the agent, rendered per case from dataset fields
    endpoint_type="chat",      # "chat" for chat-completion agents (the common case)
)
```

`prompt` is a Python format-string filled from each dataset row. Add fields if the
agent needs more context — e.g. `prompt="{input}\n\nContext:\n{context}"`.

> Anything the judge needs to *see* must be in the **agent prompt**, not only in
> the judge criteria — this is a black-box eval, so the agent only knows what the
> prompt carries. (This is why `faithfulness` injects `context` into the prompt.)

### `@scorer`

Marks the scoring function. NeMo calls it once per case with a `ScorerInput`:

- `sample.response` — the agent's raw text reply
- `sample.metadata` — the full dataset row as a `dict`

Return a `dict` of named numeric scores. **Omit the numeric key entirely** to mark
a case [inconclusive](./outputs.md) (not a failure) — the right default when a
required field is missing or the judge itself broke.

```python
@scorer
def score(sample: ScorerInput) -> dict[str, Any]:
    return evaluate_response(sample.response, sample.metadata)
```

### Keep scoring logic in a pure helper

Separating the logic into a standalone `evaluate_response(response, metadata)`
function lets unit tests import and call it directly, with no NeMo fixtures. See the
`datarobot-genai` repo's `tests/eval/test_benchmarks.py` for the pattern.

```python
def evaluate_response(response: str, metadata: dict[str, Any]) -> dict[str, Any]:
    keywords = metadata.get("required_keywords")
    if not keywords:
        return {"reason": "no required_keywords provided"}   # → inconclusive
    missing = [kw for kw in keywords if kw.lower() not in response.lower()]
    if missing:
        return {"score": 0.0, "keyword_presence": 0.0, "reason": f"missing: {missing}"}
    return {"score": 1.0, "keyword_presence": 1.0, "reason": "all present"}
```

## Judge-based benchmarks

A judge-based benchmark adds two things on top of the above.

**1. A `judge:` block in the pipeline YAML** (required). `run.py` exports
`JUDGE_URL`, `JUDGE_MODEL_ID`, and `JUDGE_API_KEY_NAME` from it before invoking the
runner. The module reads them from the environment so the same code works whether
invoked via `task eval` or run manually for debugging:

```python
JUDGE = {
    "url": os.environ.get("JUDGE_URL", "https://app.datarobot.com/api/v2/genai/llmgw"),
    "model_id": os.environ.get("JUDGE_MODEL_ID", "azure/gpt-5-5-2026-04-23"),
    "api_key": os.environ.get("JUDGE_API_KEY_NAME", "DATAROBOT_API_TOKEN"),  # env var NAME, not the token
    "temperature": 0.0,
    "max_new_tokens": 1024,
}
```

Forward this dict to the runner via `@benchmark(..., extra={"judge": JUDGE})`.

**2. A `judge_score(...)` call** inside the scorer. It makes one LLM call against
the judge endpoint. Built-in templates:

| Template | Grades → score |
|---|---|
| `likert_5` | 1-5 quality/helpfulness → 0.2..1.0 |
| `binary_qa` | PASS / FAIL |
| `binary_qa_partial` | PASS / PARTIAL / FAIL |
| `safety` | SAFE / UNSAFE |

Pass `template=<your_string>` + `grade_pattern` + `score_mapping` for a fully
custom judge prompt.

```python
@scorer
def score(sample: ScorerInput) -> dict[str, Any]:
    result = judge_score(
        sample,
        template="likert_5",
        question=sample.metadata.get("input", ""),
        criteria=sample.metadata.get("criteria", ""),  # per-case grading instructions
    )
    return _scored(result, "quality")
```

### Handle judge errors as inconclusive

`judge_score()` returns the grade `CALL_ERROR` or `PARSE_ERROR` when the LLM call
itself fails (network/HTTP error after retries) or its output can't be parsed.
Emit **no numeric score** for those, so the case is marked inconclusive instead of
counted as an agent failure:

```python
_JUDGE_ERROR_GRADES = frozenset({"CALL_ERROR", "PARSE_ERROR"})

def _scored(result: dict[str, Any], category_key: str) -> dict[str, Any]:
    grade = result["judge_grade"]
    if grade in _JUDGE_ERROR_GRADES:
        return {"judge_grade": grade}                 # no numeric key → inconclusive
    score = result["judge_score"]
    return {"score": score, category_key: score, "judge_grade": grade}
```

## Reference

- The two `user_example_*` files are commented as line-by-line tutorials.
- The built-in modules in `datarobot_genai/eval/benchmarks/` (shipped in the
  `datarobot-genai[eval]` package) are each self-contained (no shared imports) and
  make good copy-paste references.
- See [Pipelines](./pipelines.md) for the YAML schema and model-naming rules, and
  [Troubleshooting](./troubleshooting.md) for judge-model gotchas.
