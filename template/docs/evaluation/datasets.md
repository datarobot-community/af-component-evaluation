# Datasets

A dataset is a JSON array of test cases. Each benchmark is **isolated** and reads
a slightly different set of fields, so datasets are benchmark-specific — see
`user_datasets/sample_<benchmark>.json` for a ready-to-copy example of each.

## Common fields (all benchmarks)

| Field | Type | Required | Description |
|---|---|:---:|---|
| `id` | string | yes | Unique identifier for the test case |
| `input` | string | yes | The user message sent to the agent (the prompt) |
| `source` | string | no | `"collected"` (real interaction) or `"synthetic"` (generated) |
| `notes` | string | no | For judge-based benchmarks, extra grading criteria passed to the judge; otherwise human documentation |

Any extra fields you add are passed through to the benchmark verbatim, so custom
benchmarks can read whatever they need without changing the loader.

## Per-benchmark fields

| Benchmark | Judge? | Extra fields | Notes |
|---|:---:|---|---|
| `answer_quality` | ✅ | — | Likert 1-5 on `input`; `notes` guides the judge |
| `safety_refusal` | ✅ | — | Adversarial `input`; SAFE/UNSAFE |
| `faithfulness` | ✅ | `context` (string, **required**) | Answer must be grounded in `context` |
| `answer_correctness` | ⚙️ | `ideal_response` (**required**), `match_mode` (`exact`\|`normalized`\|`contains`, default `normalized`) | Deterministic match |
| `instruction_following` | ⚙️ | `constraints` (object, **required**) | See [constraint keys](./benchmarks.md#instruction_following) |
| `prompt_injection` | ⚙️ | `canary` (string or list, **required**) | Score 1.0 if canary is **absent** |
| `pii_leakage` | ⚙️ | `entity_types` (list, optional) | Limits which detectors run; default all |
| `tool_grounding` | ⚙️ | `canary` (string or list, **required**) | Score 1.0 if canary is **present** |

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

- **Collected:** copy a real agent interaction, set `"source": "collected"`, and
  fill in the benchmark's required fields. Human-reviewed collected cases are the
  most valuable — they reflect real usage.
- **Synthetic:** run `generate.py` to produce cases with Claude, then review and
  edit before committing.

## Generating synthetic cases

`generate.py` uses Claude to produce a mix of "good" and "bad" cases from a plain
description of what the agent does. **Review and edit the output before using it
in evaluations** — generated cases are a starting point, not ground truth.

```bash
task generate -- \
  --agent-description "A research assistant that answers questions concisely" \
  --n 20 \
  --output user_datasets/my_agent_cases.json
```

| Flag | Default | Description |
|---|---|---|
| `--agent-description` | (required) | What the agent does, and what it should / shouldn't do |
| `--n` | `10` | Total cases to generate (split evenly good/bad) |
| `--n-good` / `--n-bad` | — | Override the even split |
| `--output` | `user_datasets/generated_cases.json` | Output file path |
| `--append` | off | Append to the existing file instead of overwriting |

Requires `ANTHROPIC_API_KEY` (or equivalent Claude credentials) in your `.env`.
