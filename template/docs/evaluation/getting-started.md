# Getting started

This guide walks through the fastest path to a completed evaluation run. You send test prompts to an agent's OpenAI-compatible endpoint, score every response, and read aggregate results from fixed output files.

## Before you begin

Confirm the following prerequisites:

- **Python 3.11+** installed.
- **`uv`** and **`task`** (go-task) installed.
- **DataRobot CLI (`dr`)** installed if you use `dr task` to invoke the component.
- **A running agent endpoint**&mdash;typically `http://localhost:8842/v1` when the agent runs locally with `dr run dev`.
- **Credentials in the project-root `.env`** (one level above the component folder):
  - `DATAROBOT_API_TOKEN`&mdash;required for judge-based benchmarks and dataset generation.
  - `DATAROBOT_ENDPOINT`&mdash;for example `https://app.datarobot.com`.

Judge-free benchmarks (`answer_correctness`, `instruction_following`, `prompt_injection`, `pii_leakage`, `tool_grounding`) run without judge credentials.

## Step 1&mdash;Install dependencies

From the component directory (for example `evaluations/`):

```bash
task install
```

## Step 2&mdash;Pick a benchmark

Each run uses exactly one benchmark, selected by a pipeline YAML in `user_pipelines/`. Start with one of these:

| Pipeline | Judge? | Best for |
|---|---|---|
| `answer_quality.yaml` | Yes | General response quality (Likert 1–5). |
| `answer_correctness.yaml` | No | Regression testing against known answers. |
| `safety_refusal.yaml` | Yes | Harmful-request refusal (SAFE/UNSAFE). |

See [Benchmarks](./benchmarks.md) for the full menu and [Pipelines](./pipelines.md) for YAML details.

## Step 3&mdash;Prepare a dataset

Copy the sample dataset that matches your pipeline:

```bash
cp user_datasets/sample_answer_quality.json user_datasets/my_cases.json
```

Edit `my_cases.json` or generate synthetic cases:

```bash
task generate -- \
  --agent-description "A research assistant that answers questions concisely" \
  --pipeline user_pipelines/answer_quality.yaml \
  --n 10 \
  --output user_datasets/my_cases.json
```

Review generated cases before using them in evaluations. See [Datasets](./datasets.md) for the full schema.

## Step 4&mdash;Validate inputs

Run a dry-run to confirm the endpoint, pipeline, and dataset without scoring any cases:

```bash
task eval -- \
  --endpoint http://localhost:8842/v1 \
  --pipeline answer_quality.yaml \
  --dataset  user_datasets/my_cases.json \
  --dry-run
```

Exit code `0` means validation passed. No `output/eval_results.json` is written.

## Step 5&mdash;Run the evaluation

Remove `--dry-run` to execute the full run:

```bash
task eval -- \
  --endpoint http://localhost:8842/v1 \
  --pipeline answer_quality.yaml \
  --dataset  user_datasets/my_cases.json
```

With the DataRobot CLI from the project root:

```bash
dr task run evaluations:eval -- \
  --endpoint http://localhost:8842/v1 \
  --pipeline answer_quality.yaml \
  --dataset  user_datasets/my_cases.json
```

Replace `evaluations` with your component namespace if you renamed the folder during setup.

## Step 6&mdash;Read results

Poll progress in `output/eval_status.json`. On success, read `output/eval_results.json`:

```bash
task summarize
```

Lead with `summary.pass_rate` and `summary.mean_score`, then inspect failed or inconclusive cases by `id`. See [Outputs](./outputs.md) for the full schema.

## Common next steps

- **Compare agent versions**&mdash;run the same pipeline and dataset after a model or prompt change.
- **Add collected cases**&mdash;copy real agent interactions into JSON with `"source": "collected"`.
- **Author a custom benchmark**&mdash;copy `user_example_*` templates in `user_pipelines/`. See [Writing your own benchmark](./writing-benchmarks.md).
- **Inspect agent internals**&mdash;use NAT `/evaluate` for trajectories and tool use. See [NAT vs. NeMo](./nat-vs-nemo.md).

## See also

- [Evaluation overview](./README.md)&mdash;execution model and file structure.
- [Troubleshooting](./troubleshooting.md)&mdash;judge model names and known limitations.
