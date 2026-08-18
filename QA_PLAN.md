# QA plan&mdash;`af-component-evaluation`

Manual QA plan to complement the automated unit/integration suite. The goal is **not** exhaustive coverage&mdash;it is a small set of real user flows that a human runs end-to-end and eyeballs the results. Automated tests already cover the internals; these tests confirm the component behaves correctly when a person drives it the way a real user would.

## What this component does (one paragraph)

It is a batch evaluation component for DataRobot agents. A user picks a **pipeline** (one of 8 benchmarks), points it at an **agent endpoint** (OpenAI-compatible) and a **dataset** of test cases, and runs `run.py`. The component sends each prompt to the agent, scores the response (LLM-as-judge for 3 benchmarks, deterministic checks for the other 5), and writes results to `output/eval_results.json` plus a status file at `output/eval_status.json`.

## Scope

- **In scope:** the three CLI entry points (`run.py`, `generate.py`, `summarize.py`), the fixed output contract (`output/eval_status.json`, `output/eval_results.json`), validation/error handling, and both judge-based and judge-free benchmarks.
- **Out of scope:** the NeMo BYOB internals, the `datarobot-genai[eval]` engine itself, and benchmark scoring accuracy (covered by unit tests). QA verifies the *flows and outputs*, not the scoring math.

## Prerequisites for the tester

| Item | Notes |
|---|---|
| `uv`, `dr` CLI, Python 3.11+ | See README "Prerequisites". |
| `DATAROBOT_API_TOKEN` + `DATAROBOT_ENDPOINT` | In `.env` at project root. Required for judge-based runs and `generate.py`. |
| An agent endpoint to test against | A local DRUM agent (`http://localhost:8842/v1`) or any OpenAI-compatible endpoint. No `AGENT_API_KEY` needed for a local agent. |
| Component installed | `task install` (runs `uv sync` + component deps). |

Run commands from the component directory (`template/[[ evaluation_app_name ]]/` in source, or the rendered project root in a real install).

---

## Test cases

Each test: run the steps, record **PASS/FAIL** and any notes. Aim for ~30–45 min total.

### QA-1&mdash;Install and environment sanity
**Objective:** A fresh setup installs cleanly and credentials are wired.
1. From the project root run `task install`.
2. Confirm it completes with no errors.
3. Confirm `.env` contains `DATAROBOT_API_TOKEN` and `DATAROBOT_ENDPOINT`.

**Expected:** Install succeeds; both env vars resolve (e.g. `echo $DATAROBOT_ENDPOINT` after sourcing `.env`).

---

### QA-2&mdash;Dry-run validation (no judge cost)
**Objective:** Input validation works before any agent/judge calls are made.
```bash
uv run python run.py \
  --endpoint http://localhost:8842/v1 \
  --pipeline answer_quality.yaml \
  --dataset user_datasets/sample_answer_quality.json \
  --dry-run
```
**Expected:** Exits **0**. Reports that endpoint, pipeline YAML, benchmark module, and dataset all validated. **No** `output/eval_results.json` is written.

---

### QA-3&mdash;Happy path: judge-based benchmark (answer_quality)
**Objective:** Full end-to-end LLM-as-judge run produces a valid result file.
*Precondition:* agent endpoint reachable; DR credentials set.
```bash
uv run python run.py \
  --endpoint http://localhost:8842/v1 \
  --pipeline answer_quality.yaml \
  --dataset user_datasets/sample_answer_quality.json
```
**Expected:**
- Exit code **0**.
- `output/eval_status.json` ends at `"status": "complete"` with a `run_id`, the pipeline name, and `error: null`.
- `output/eval_results.json` exists and contains: `total_cases`, a `summary` block (`scored_cases`, `inconclusive_cases`, `mean_score`, `pass_rate`), and a `cases` array where each case has `agent_response`, `score`, `passed`, and `reason`.
- Per-case `score` values look sane (between 0 and 1), not all null.

---

### QA-4&mdash;Judge-free benchmark (answer_correctness) with no judge creds
**Objective:** A deterministic benchmark runs without any judge model / credentials and is reproducible.
1. Confirm `user_pipelines/answer_correctness.yaml` has **no** `judge:` block.
2. Run:
```bash
uv run python run.py \
  --endpoint http://localhost:8842/v1 \
  --pipeline answer_correctness.yaml \
  --dataset user_datasets/sample_answer_correctness.json
```
3. Run it a **second** time and compare summaries.

**Expected:** Exit **0**; `eval_results.json` written; `inconclusive_cases` is 0 (no judge involved); results are identical across both runs (deterministic). Cases show `score` and `reason`, not judge grades.

---

### QA-5&mdash;Generate synthetic test cases
**Objective:** `generate.py` produces a reviewable dataset.
```bash
uv run python generate.py \
  --agent-description "A research assistant that answers questions concisely" \
  --n 10 \
  --output user_datasets/qa_generated.json
```
**Expected:** File is written with ~10 cases. Open it: each case has an `id`, `input`, and `expected_behavior` (`good`/`bad`). The prompts are relevant to the described agent. (This is a human judgment call&mdash;do the cases look usable?)

---

### QA-6&mdash;View results
**Objective:** `summarize.py` renders a readable summary of a completed run.
```bash
uv run python summarize.py output/
```
**Expected:** A formatted summary prints&mdash;per-case table with IDs, scores (2 decimals), and pass/fail markers (✓/✗), plus the aggregate rates. Numbers match what's in `output/eval_results.json` from QA-3 or QA-4.

---

### QA-7&mdash;Error handling: unreachable / invalid inputs
**Objective:** Failures are reported cleanly, not as a stack-trace crash.

Run each and check the exit code + status file:

| Sub-case | Command tweak | Expected exit | Expected `eval_status.json` |
|---|---|---|---|
| 7a Bad endpoint | `--endpoint http://localhost:9999/v1` (nothing listening) | **1** (validation) | `status: failed`, `error` describes unreachable endpoint |
| 7b Missing pipeline | `--pipeline does_not_exist.yaml` | **1** | `status: failed`, error names the missing pipeline |
| 7c Missing dataset | `--dataset user_datasets/nope.json` | **1** | `status: failed`, error names the missing dataset |

**Expected overall:** No uncaught Python traceback dumped to the user; each failure leaves `eval_status.json` at `"failed"` with a human-readable `error`.

---

### QA-8&mdash;(Optional / advanced) Inconclusive case handling
**Objective:** A case where the agent answers but the **judge call fails** (e.g. the judge endpoint applies input content filtering to an adversarial prompt) is marked *inconclusive*, not a 0.0 failure.
1. Run a judge-based pipeline against `sample_safety_refusal.json` or `sample_prompt_injection.json`.
2. Inspect the summary.

**Expected:** Any judge-failed case has `score: null` and `passed: null`, is counted in `inconclusive_cases`, and is **excluded** from `pass_rate`/`mean_score`. Rates are computed over scored cases only. (See
[`outputs.md`](template/docs/evaluation/outputs.md).)

---

## Regression smoke tests (automated, run alongside human QA)

The repo ships live integration smoke tests that exercise all three CLI commands against the real DR gateway. QA should run these once per cycle as a fast credential/gateway health check:

```bash
task test-integration          # requires DATAROBOT_API_TOKEN + DATAROBOT_ENDPOINT in .env
# or: uv run python -m pytest -m integration -vv
```

These cover: a one-case `answer_quality` end-to-end run (agent → judge → metric → normalization), `summarize` output rendering, and one synthetic `generate` call. If they fail, stop and fix before continuing manual QA&mdash;it usually means credentials or the gateway, not the component.

---

## Sign-off

| Test | Result | Tester | Date | Notes |
|---|---|---|---|---|
| QA-1 Install | | | | |
| QA-2 Dry-run | | | | |
| QA-3 Judge-based run | | | | |
| QA-4 Judge-free run | | | | |
| QA-5 Generate cases | | | | |
| QA-6 Summarize | | | | |
| QA-7 Error handling | | | | |
| QA-8 Inconclusive (opt) | | | | |
| Smoke tests | | | | |
