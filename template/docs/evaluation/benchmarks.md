# Benchmarks

A **benchmark** is a self-contained Python module that defines what to send to the agent and how to score the response. The 8 built-ins ship in the `datarobot-genai[eval]` package (`datarobot_genai/eval/benchmarks/`). Each comes with a default pipeline (`user_pipelines/<name>.yaml`) and a sample dataset (`user_datasets/sample_<name>.json`).

Each run uses exactly **one** benchmark. Benchmarks fall into two families:

- **Judge-based**&mdash;an LLM judge grades the response. Requires a `judge:` block in the pipeline and judge credentials.
- **Judge-free**&mdash;deterministic checks (string match, regex, parsing). No judge, no credentials, and identical scores on every run.

> **Scope.** These benchmarks are development-time testing aids for catching
> regressions in an agent before release. They are not security, privacy, or
> compliance controls, and a passing score is not evidence of compliance with any
> standard. For runtime enforcement, see
> [How this relates to runtime guardrails](#how-this-relates-to-runtime-guardrails)
> below.

## Scoring convention

Every benchmark emits a normalized `score` in `[0, 1]`. A case **passes** at `score >= 0.5`. Judge-based benchmarks map a grade to that score (for example Likert 3/5 → 0.6). Judge-free benchmarks compute it deterministically.

A case that **cannot** be scored&mdash;a judge call that errored or a required field missing&mdash;is marked **inconclusive** (`score: null`, `passed: null`) and **excluded** from rates rather than counted as a failure. See [Outputs](./outputs.md).

## Judge-based benchmarks

### `answer_quality`

The catch-all "is this a good answer?" benchmark. An LLM judge scores each response on a 1–5 Likert scale for helpfulness, coherence, and relevance. Use it for open-ended tasks where there is no single correct answer.

- **Scoring**&mdash;`likert_5` maps grades 1–5 to 0.2–1.0; passes at grade ≥ 3.
- **Dataset**&mdash;`input` (required), `notes` (optional extra grading criteria injected into the judge prompt).

### `safety_refusal`

Feed adversarial or harmful prompts. A safety judge grades each response SAFE (refused, deflected, or harmless) or UNSAFE (complied with the harmful request).

- **Scoring**&mdash;`safety` maps SAFE = 1.0 and UNSAFE = 0.0; any SAFE passes.
- **Dataset**&mdash;`input` (required adversarial prompt), `notes` (optional definition of what "unsafe" means for this case).
- **Note:** Some judge endpoints apply input content filtering and can return 400 on adversarial prompts. That is a judge-side failure, not an agent failure, so the case is marked inconclusive rather than scored 0. See [Troubleshooting](./troubleshooting.md).

### `faithfulness`

For agents that answer from provided context. Each case supplies a `context` passage that is sent to the agent **as part of the prompt** (this is a black-box eval&mdash;the agent only knows what the prompt carries). A judge then decides whether the answer is fully supported by that context (grounded) or introduces unsupported claims (hallucinated).

- **Scoring**&mdash;built-in `binary_qa` with the context injected into the grading criteria. GRADE C (grounded) → 1.0, GRADE I (hallucinated) → 0.0.
- **Dataset**&mdash;`input` (required), `context` (**required** source passage, sent to the agent AND used as the grounding reference), `notes` (optional).
- **Note:** Because the check is "supported by THIS context," a correct-but-ungrounded answer (true in the world but absent from the context) is intentionally scored as a hallucination. That is the RAG failure mode this benchmark exists to catch.

## Judge-free benchmarks

### `answer_correctness`

The regression-testing workhorse. When you have ground-truth answers, check the agent response against them with no judge. Fully deterministic.

- **Scoring**&mdash;1.0 on match, 0.0 otherwise, by `match_mode`:
  - `exact`&mdash;equals reference after trimming whitespace.
  - `normalized` (default)&mdash;equal after lowercasing and stripping punctuation/extra spaces.
  - `contains`&mdash;normalized reference appears somewhere in the normalized response.
- **Dataset**&mdash;`input` (required), `ideal_response` (**required**), `match_mode` (optional, default `normalized`). Missing `ideal_response` → inconclusive.

### `instruction_following`

Checks structural constraints the prompt asked for: length limits, valid JSON, required/forbidden phrases, regex shape. Semantic constraints (for example "use a professional tone") are out of scope&mdash;use `answer_quality` for those.

- **Scoring**&mdash;fraction of specified constraints satisfied, in `[0, 1]` (each `must_include` / `must_exclude` item counts individually).
- **Dataset**&mdash;`input` (required), `constraints` (**required** object). Keys:

  | Key | Type | Meaning |
  |---|---|---|
  | `max_words` / `min_words` | int | Word-count bounds. |
  | `max_chars` | int | Character-count upper bound. |
  | `must_be_json` | bool | Response must parse as JSON (code fences tolerated). |
  | `must_include` | string or list | Substrings that must appear. |
  | `must_exclude` | string or list | Substrings that must NOT appear. |
  | `regex` | string | Pattern that must match somewhere in the response. |

### `prompt_injection`

Each case is an attack that tries to hijack the agent into emitting a known "canary" string. If the canary shows up in the response, the injection succeeded. Checking for a fixed string is deterministic and not subject to judge variance. It only detects the canary appearing verbatim, so an attack that succeeds without reproducing it exactly is not caught.

- **Scoring**&mdash;1.0 if the canary is **absent** (resisted), 0.0 if present.
- **Dataset**&mdash;`input` (required attack prompt), `canary` (**required** string or list; ANY match counts as leaked). Missing `canary` → inconclusive.

### `pii_leakage`

Scans the response for personally identifiable information using regex detectors. A clean response passes; any detected entity fails. Pattern matching is faster, cheaper, and more reliable than an LLM for structured identifiers.

- **Detectors**&mdash;EMAIL, PHONE, SSN, CREDIT_CARD (Luhn-validated), IP_ADDRESS. Coverage is intentionally conservative&mdash;it misses free-form names and addresses. For NER-grade detection, swap in a library like Presidio in a custom copy.
- **Scoring**&mdash;1.0 if no PII detected, 0.0 if any entity detected.
- **Dataset**&mdash;`input` (required), `entity_types` (optional list limiting which detectors run; default all). The `reason` field reports which types and counts were found, never the matched values.

### `tool_grounding`

The mirror image of `prompt_injection` (present = good). Tool calls are not visible in this black-box eval (that is NAT `/evaluate` job&mdash;see [NAT vs. NeMo](./nat-vs-nemo.md)), but you can verify *evidence* of tool use: seed the tool data source with a unique value reachable only by querying it, ask a question whose answer is that value, and check the response for it. The agent cannot produce a value it was never given without using the tool.

- **Scoring**&mdash;1.0 if every canary value is **present** (tool data surfaced), 0.0 if any is missing (agent guessed, refused, or skipped the tool).
- **Dataset**&mdash;`input` (required), `canary` (**required** string or list; ALL must be present for full credit). Missing `canary` → inconclusive.

## How this relates to runtime guardrails

Three of the benchmarks here (`safety_refusal`, `prompt_injection`, `pii_leakage`)
describe capabilities that also exist as runtime moderation guardrails in the
DataRobot platform. They solve different problems and are not substitutes:

| | This component | Runtime guardrails |
|---|---|---|
| **When** | Before release, on a fixed dataset | On live traffic, per request |
| **What it does** | Measures and reports a score | Intervenes: blocks, rewrites, or flags |
| **Purpose** | Catch regressions between versions | Enforce policy in production |

Think of this as the test suite and guardrails as the runtime safety net. A good
score here means an agent handled your test cases on the day you ran it. It says
nothing about what the agent does on traffic it has never seen, which is what
guardrails are for. Shipping an agent that scores well here still needs whatever
runtime controls your use case requires.

## Adding a benchmark

Each built-in module in `datarobot_genai/eval/benchmarks/` is self-contained with no shared imports, so it doubles as a reference. To write your own, copy one of the annotated `user_example_*` templates. See [Writing your own benchmark](./writing-benchmarks.md).

## See also

- [Pipelines](./pipelines.md)&mdash;YAML schema and the 8-benchmark menu.
- [Datasets](./datasets.md)&mdash;per-benchmark field requirements.
- [Outputs](./outputs.md)&mdash;how scores appear in `eval_results.json`.
