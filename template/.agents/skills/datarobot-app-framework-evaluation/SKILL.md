---
name: datarobot-app-framework-evaluation
description: >-
  Run batch, black-box evaluations of a DataRobot agent with the App Framework
  evaluation component (NeMo Evaluator BYOB). Use when the user wants to score an
  agent's responses at scale, build or generate an evaluation dataset, regression-test
  an agent after a change, check safety/quality/correctness, or run/interpret the
  `eval` task. Covers preparing evaluation data, picking a benchmark, executing the
  evaluator, and reading results.
---

# DataRobot App Framework — Evaluation

Run **batch, black-box evaluations** of a DataRobot agent: send each test prompt to
the agent's OpenAI-compatible endpoint, score every response, and report aggregate
quality/safety/correctness. Built on the NeMo Evaluator **BYOB** framework — runs
in-process (no Docker, no GPUs) and ships **8 isolated benchmarks**.

This skill teaches the end-to-end workflow: **prepare data → pick a benchmark →
run → read results**. Deep reference material lives in `docs/evaluation/` — load the
specific file when you need field-level detail rather than copying it here.

## Trigger conditions

Use this skill when the user wants to:

- Evaluate, score, or grade a DataRobot agent's responses at scale
- Regression-test an agent after an LLM upgrade or prompt change ("did anything break?")
- Run a safety, quality, correctness, faithfulness, PII, or prompt-injection check
- Build, generate, or convert an evaluation dataset / set of test cases
- Run `dr task run evaluations:eval` / `run.py`, or interpret `eval_results.json` / `eval_status.json`

Do **not** use this for inspecting agent *internals* (tool calls, trajectories, RAG
retrieval). That is NAT `/evaluate`'s job — see `docs/evaluation/nat-vs-nemo.md`.

## Step 0 — Locate the component and confirm the agent is reachable

The evaluation component folder was named during setup. The default is `evaluations/`
(task namespace: `evaluations:`), but the user can rename it.

**Run all commands from the project root.** The DataRobot CLI's `dr task` composes
the project's root Taskfile on the fly (so the user controls their own
`Taskfile.yml`), routes into the evaluation component under the component's
namespace, and loads `.env` from the project root (which carries
`DATAROBOT_API_TOKEN` and `DATAROBOT_ENDPOINT`). Pass task args after `--`:

```bash
dr task run evaluations:<task> -- <task args>
```

**If `dr task run evaluations:<task>` fails with a "task not found" error**, recover the
namespace in this order:

1. Inspect the composed Taskfile directly — this bypasses `dr` entirely and is the ground truth:
   ```bash
   task --list
   ```
   Pick the `<namespace>:eval`-style entry and re-run as `dr task run <namespace>:eval -- ...`.
2. If `task --list` shows no `<namespace>:` entries at all, the project Taskfile hasn't been
   composed yet (fresh checkout, or a new component was added). Compose it, then list again:
   ```bash
   dr task compose && task --list
   ```
3. If `task --list` still shows nothing for evaluation, read the copier answers file to confirm
   the configured component name:
   ```bash
   ls .datarobot/answers/evaluation-*.yml
   ```
   The filename's `<name>` is the namespace (`evaluation_app_name:` inside confirms it).

The agent under test must be serving an OpenAI-compatible endpoint. For local dev,
the agent component is typically started with `dr run dev` (default
`http://localhost:8842/v1`). Confirm with the user what endpoint to target before
running anything. To verify the agent is up, run Step 4 with `--dry-run` — it uses the
same reachability rules as a real run.

## Step 1 — Pick what to measure (the benchmark)

Each run uses exactly **one** benchmark, selected by a pipeline YAML in
`user_pipelines/`. Help the user choose from the 8 defaults:

| Pipeline | Judge? | Measures |
|---|:---:|---|
| `answer_quality.yaml` | ✅ judge | General response quality (Likert 1–5) |
| `safety_refusal.yaml` | ✅ judge | Refuses harmful requests (SAFE/UNSAFE) |
| `faithfulness.yaml` | ✅ judge | Answer grounded in a RAG `context` |
| `answer_correctness.yaml` | ⚙️ none | Matches a known answer |
| `instruction_following.yaml` | ⚙️ none | Obeys structural constraints |
| `prompt_injection.yaml` | ⚙️ none | Resists hijack — a `canary` must NOT appear |
| `pii_leakage.yaml` | ⚙️ none | No PII in the response |
| `tool_grounding.yaml` | ⚙️ none | Used its tool/data — a `canary` MUST appear |

**Judge-based** benchmarks need a judge model + credentials (Step 3). **Judge-free**
ones are deterministic and need none. For the full meaning of each benchmark and its
scoring, load `docs/evaluation/benchmarks.md`; for the pipeline YAML schema, load
`docs/evaluation/pipelines.md`. You rarely edit a pipeline — usually just point
`--dataset` at your data.

## Step 2 — Get the evaluation data

A dataset is a JSON array of test cases. Every benchmark reads `id` + `input`, plus
benchmark-specific fields (`context`, `ideal_response`, `canary`, `constraints`, …).
**Always confirm the dataset matches the chosen benchmark** — load
`docs/evaluation/datasets.md` for the per-benchmark field table before building data.

Prompt the user to pick the source:

1. **Collected (best)** — real agent interactions, `"source": "collected"`. Most
   valuable because they reflect real usage. Copy them into the JSON shape and fill
   the benchmark's required fields.
2. **From a spreadsheet** — convert a CSV (`id, source, input` required):
   ```bash
   dr task run evaluations:convert -- user_datasets/my_cases.csv
   ```
3. **Synthetic** — generate a good/bad mix with an LLM from a description of the agent.
   Pass `--pipeline` to tailor criteria and required fields to the specific benchmark:
   ```bash
   dr task run evaluations:generate -- \
     --agent-description "A research assistant that answers questions concisely" \
     --pipeline user_pipelines/answer_quality.yaml \
     --n 20 \
     --output user_datasets/my_agent_cases.json
   ```

> ⚠️ **Synthetic cases are a starting point, not ground truth.** Always have the user
> review and edit generated cases before evaluating against them. Generation requires
> `DATAROBOT_API_TOKEN` and `DATAROBOT_ENDPOINT` in the project-root `.env` (one
> level above the component folder — same credentials used for judge-based runs).
> When `--pipeline` points at a judge-based pipeline, generation pings the judge
> endpoint up front and exits 1 on failure — catches bad tokens before any calls.

A ready-to-copy `user_datasets/sample_<benchmark>.json` exists for every benchmark —
start from the one matching your chosen pipeline.

If you cannot determine the purpose of the agent from an agent-spec.md or the README.md ask the
user for the --agent-description field instead of rifling through the code.

## Step 3 — Configure judge credentials (judge-based benchmarks only)

Skip entirely for judge-free benchmarks. For judge-based ones, set in the project-root `.env` (one level above the component folder):

| Variable | Required | Purpose |
|---|:---:|---|
| `DATAROBOT_API_TOKEN` | yes | Bearer token for the DR LLM gateway (judge runs and `dr task run evaluations:generate`) |
| `DATAROBOT_ENDPOINT` | yes | DataRobot endpoint URL (e.g. `https://app.datarobot.com`) |
| `AGENT_API_KEY` | no | Bearer token for the agent endpoint; only sent if set |

> ⚠️ **Judge model gotcha:** use an **Azure** GPT judge (e.g. `azure/gpt-5-5-2026-04-23`),
> a gateway **catalog** name with **no `datarobot/` prefix**. Bedrock/Claude models
> reject NeMo's judge call (it sends both `temperature` and `top_p`). See
> `docs/evaluation/troubleshooting.md`.

Judge-based runs **preflight** the judge endpoint at startup: one ping to
`{judge.url}/chat/completions` with the configured token + model. Non-200 →
`eval_status.json` is written as `failed` and the run exits 1 before any cases
are scored. Judge-free pipelines skip the check entirely.

## Step 4 — Run the evaluation

Always validate first with `--dry-run`, then run:

```bash
# Validate inputs without executing
dr task run evaluations:eval -- \
  --endpoint http://localhost:8842/v1 \
  --pipeline answer_quality.yaml \
  --dataset  user_datasets/sample_answer_quality.json \
  --dry-run

# Run for real (drop --dry-run)
dr task run evaluations:eval -- \
  --endpoint http://localhost:8842/v1 \
  --pipeline answer_quality.yaml \
  --dataset  user_datasets/sample_answer_quality.json
```

`--pipeline` is a filename in `user_pipelines/`. `--dataset` defaults to
`user_datasets/sample_answer_quality.json` if omitted. Exit codes: `0` success ·
`1` validation error · `2` runner failed · `3` normalization failed.


## Step 5 — Read the results

Output paths are fixed:

```bash
dr task run evaluations:summarize    # pretty-prints output/eval_results.json
```

- `output/eval_status.json` — `running` → `complete` | `failed` (poll this for progress).
- `output/eval_results.json` — written on success: `summary` (pass rates, mean scores)
  + per-case `cases[]` (response, score, pass/fail, judge reason).

Rates are computed over **scored** cases only. A case that can't be fairly graded
(e.g. the judge call itself errors, or a required field is missing) is marked
**inconclusive** (`score: null`, `passed: null`) and excluded from rates —
reported separately under `inconclusive_cases`. See `docs/evaluation/outputs.md`.

When reporting back to the user, lead with the pass rate and mean score, then surface
any failed or inconclusive cases by `id`.

## Custom benchmarks

If none of the 8 fit, the user can author a custom benchmark + pipeline by copying the
annotated `user_example_*` templates in `user_pipelines/`. Load
`docs/evaluation/writing-benchmarks.md` for the full guide.

## Dependencies and prerequisites

- **Tools:** `uv`, `task` (go-task), the DataRobot CLI (`dr`), and a running agent
  endpoint. `dr run` is a thin wrapper around `task` — it composes the project's
  Taskfile on demand and shells out to the `task` binary, so both must be installed.
- **Env vars** (in the project-root `.env`, one level above the component folder):
  `DATAROBOT_API_TOKEN` and `DATAROBOT_ENDPOINT` (judge runs and `dr task run evaluations:generate`),
  `AGENT_API_KEY` (optional agent auth).
- **Network:** judge-based runs call the DR LLM gateway; judge-free runs and the agent
  endpoint may be fully local/offline.

## Context cost

Loading this `SKILL.md` is small (~1.5k tokens). The reference docs in
`docs/evaluation/` are loaded on demand — read only the one you need:
`datasets.md`, `pipelines.md`, and `benchmarks.md` are the most common (~1–2k tokens
each). Avoid loading all of `docs/evaluation/` at once.

## See also

- `docs/evaluation/getting-started.md` — install through first completed run
- `docs/evaluation/README.md` — component overview and execution model
- `docs/evaluation/pipelines.md` · `benchmarks.md` · `datasets.md` — reference detail
- `docs/evaluation/outputs.md` — result/status schemas and lifecycle
- `docs/evaluation/troubleshooting.md` — judge-model gotchas and known limits
- `docs/evaluation/nat-vs-nemo.md` — when to use NAT `/evaluate` instead
