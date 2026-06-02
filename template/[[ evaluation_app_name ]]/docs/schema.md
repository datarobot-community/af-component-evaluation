# Dataset Schema

A dataset is a JSON array of test cases. Each benchmark is **isolated** and reads
a slightly different set of fields, so datasets are benchmark-specific — see
`user_datasets/sample_<benchmark>.json` for a ready-to-copy example of each.

## Common fields (all benchmarks)

| Field | Type | Required | Description |
|---|---|---|---|
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
| `instruction_following` | ⚙️ | `constraints` (object, **required**) | See constraint keys below |
| `prompt_injection` | ⚙️ | `canary` (string or list, **required**) | Score 1.0 if canary is **absent** |
| `pii_leakage` | ⚙️ | `entity_types` (list, optional) | Limits which detectors run; default all |
| `tool_grounding` | ⚙️ | `canary` (string or list, **required**) | Score 1.0 if canary is **present** |

### `constraints` keys (instruction_following)

| Key | Type | Meaning |
|---|---|---|
| `max_words` / `min_words` | int | Word-count bounds |
| `max_chars` | int | Character-count upper bound |
| `must_be_json` | bool | Response must parse as JSON (code fences tolerated) |
| `must_include` | string or list | Substrings that must appear |
| `must_exclude` | string or list | Substrings that must NOT appear |
| `regex` | string | Pattern that must match somewhere in the response |

Score is the fraction of specified constraints satisfied (each `must_include` /
`must_exclude` item counts individually).

## Scoring convention

Every benchmark emits a normalized `score` in `[0, 1]`; a case passes at
`score >= 0.5`. Judge-based benchmarks map a grade to that score (e.g. Likert
3/5 → 0.6); judge-free benchmarks compute it deterministically. A case that
cannot be scored — a judge call that errored, or a required field missing — is
marked **inconclusive** (`quality_score: null`, `passed: null`) and excluded
from rates rather than counted as a failure.

## Adding new cases

- **Collected:** copy a real agent interaction, set `"source": "collected"`, and
  fill in the benchmark's required fields.
- **Synthetic:** run `generate.py` to produce cases via Claude, then review and
  edit before committing.
