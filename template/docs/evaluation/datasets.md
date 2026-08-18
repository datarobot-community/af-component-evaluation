# Datasets

A dataset is a JSON array of test cases. Each benchmark is **isolated** and reads a slightly different set of fields, so datasets are benchmark-specific. See `user_datasets/sample_<benchmark>.json` for a ready-to-copy example of each.

## Common fields (all benchmarks)

| Field | Type | Required | Description |
|---|---|:---:|---|
| `id` | string | yes | Unique identifier for the test case. |
| `input` | string | yes | The user message sent to the agent (the prompt). |
| `source` | string | no | `"collected"` (real interaction) or `"synthetic"` (generated). |
| `expected_behavior` | string | no | `"good"` or `"bad"`&mdash;whether a well-behaved agent should succeed or the case probes a failure. Drives the good/bad pass-rate split in the output; the generator always sets it. |
| `notes` | string | no | For judge-based benchmarks, extra grading criteria passed to the judge; otherwise human documentation. |

Any extra fields you add are passed through to the benchmark verbatim, so custom benchmarks can read whatever they need without changing the loader.

A machine-readable JSON Schema for the full case shape (common plus per-benchmark fields, and what the generator always emits) lives at [`schemas/dataset_schema.json`](./schemas/dataset_schema.json).

## Per-benchmark fields

| Benchmark | Judge? | Extra fields | Notes |
|---|:---:|---|---|
| `answer_quality` | Yes | — | Likert 1–5 on `input`; `notes` guides the judge. |
| `safety_refusal` | Yes | — | Adversarial `input`; SAFE/UNSAFE. |
| `faithfulness` | Yes | `context` (string, **required**) | Answer must be grounded in `context`. |
| `answer_correctness` | No | `ideal_response` (**required**), `match_mode` (`exact`\|`normalized`\|`contains`, default `normalized`) | Deterministic match. |
| `instruction_following` | No | `constraints` (object, **required**) | See [constraint keys](./benchmarks.md#instruction_following). |
| `prompt_injection` | No | `canary` (string or list, **required**) | Score 1.0 if canary is **absent**. |
| `pii_leakage` | No | `entity_types` (list, optional) | Limits which detectors run; default all. |
| `tool_grounding` | No | `canary` (string or list, **required**) | Score 1.0 if canary is **present**. |

See [Benchmarks](./benchmarks.md) for the full meaning of each field.

## Example case

```json
{
  "id": "good-002",
  "input": "Explain the differences between RAG and fine-tuning",
  "source": "collected",
  "notes": "Should mention retrieval vs. weight updates and a trade-off"
}
```

## Adding cases

- **Collected**&mdash;copy a real agent interaction, set `"source": "collected"`, and fill in the required fields for the benchmark. Human-reviewed collected cases are the most valuable because they reflect real usage.
- **Synthetic**&mdash;run `generate.py` to produce cases with a DataRobot-hosted model, then review and edit before committing.
- **From CSV**&mdash;if your cases live in a spreadsheet, export to CSV and run `generate.py --convert` to produce the JSON file (see below).

## Generating synthetic cases

`generate.py` uses a DataRobot-hosted model via LiteLLM to produce a mix of "good" and "bad" cases from a plain description of what the agent does.

**Important**: Review and edit the output before using it in evaluations. Generated cases are a starting point, not ground truth.

Pass `--pipeline` to tailor the prompt to the specific benchmark being evaluated: what "good" vs "bad" means, and which extra fields (for example, `canary`, `constraints`, `context`) are required for that benchmark.

```bash
task generate -- \
  --agent-description "A research assistant that answers questions concisely" \
  --pipeline user_pipelines/answer_quality.yaml \
  --n 20 \
  --output user_datasets/my_agent_cases.json
```

| Flag | Default | Description |
|---|---|---|
| `--agent-description` | (required) | What the agent does and what it should or should not do. |
| `--pipeline` | — | Pipeline YAML to tailor good/bad criteria and required fields to the benchmark. |
| `--n` | `10` | Total cases to generate (split evenly good/bad). |
| `--n-good` / `--n-bad` | — | Override the even split. |
| `--output` | `user_datasets/generated_cases.json` | Output file path. |
| `--append` | off | Append to the existing file instead of overwriting. |

Requires `DATAROBOT_API_TOKEN` and `DATAROBOT_ENDPOINT` in your `.env`.

## Converting from CSV

If you or a colleague maintains cases in a spreadsheet, export to `.csv` and convert with `generate.py --convert` rather than hand-writing JSON.

```bash
# Convert CSV to JSON (writes user_datasets/my_cases.json by default).
task generate -- --convert user_datasets/my_cases.csv

task generate -- --convert user_datasets/my_cases.csv --output user_datasets/answer_quality.json
```

### CSV format

- **Row 0** is the header (column names).
- **Rows 1+** are individual test cases.
- **Every column becomes a JSON field**&mdash;nothing is dropped.
- **Empty cells** come through as `""` (CSV has no native null; edit the JSON afterward if a field such as `ideal_response` should be `null`).

### Required columns

| Column | Notes |
|---|---|
| `id` | Unique identifier&mdash;must be present and non-empty. |
| `source` | `"collected"` or `"synthetic"`. |
| `input` | The user message sent to the agent. |

The converter raises an error if any of these columns are missing from the header row.

### Recommended columns

| Column | Notes |
|---|---|
| `notes` | Grading criteria for judge benchmarks; human docs for others. A warning is printed if absent. |

Any benchmark-specific columns (`context`, `ideal_response`, `canary`, and so on) are also carried over automatically&mdash;include them in the spreadsheet.

### CSV example

`user_datasets/sample_answer_quality.csv` is a ready-to-open example that produces exactly the same cases as `sample_answer_quality.json`:

```csv
id,source,input,notes
quality-001,collected,"Explain the difference between RAG and fine-tuning for LLM customization.","Technical question — reward an accurate, well-structured, concise answer."
quality-002,synthetic,"Write a short, upbeat blog post introduction about the future of autonomous vehicles.","Open-ended creative task — reward coherent, on-topic, engaging prose."
```

## See also

- [Benchmarks](./benchmarks.md)&mdash;how each benchmark uses dataset fields.
- [Getting started](./getting-started.md)&mdash;prepare a dataset for your first run.
- [Writing your own benchmark](./writing-benchmarks.md)&mdash;custom fields for custom benchmarks.
