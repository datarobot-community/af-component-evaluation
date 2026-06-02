# Example Run

`run.py` is invoked by the external CLI with flags. This documents what those flags correspond to.

## Usage

```sh
python run.py \
  --endpoint  http://localhost:8080/v1 \
  --pipeline  answer_quality.yaml \
  --dataset   user_datasets/sample_answer_quality.json
```

Pick any pipeline from `user_pipelines/` (8 defaults ship; see that folder's
README). Judge-free pipelines (e.g. `pii_leakage.yaml`, `prompt_injection.yaml`)
need no judge credentials.

## Required environment variables

| Variable | Description |
|---|---|
| `AGENT_API_KEY` | API key for the agent endpoint |
| `AGENT_MODEL_NAME` | Model name the agent endpoint expects |
| `JUDGE_API_KEY` | API key for the judge LLM (judge-based pipelines only) |

The judge model and URL are set in the pipeline YAML, not here. Judge-free
pipelines omit the `judge:` block and need no judge key.

## Optional environment variables

| Variable | Default | Description |
|---|---|---|
| `MAX_CONCURRENCY` | `4` | Parallel requests to the agent |

## Arguments

| Flag | Example | Description |
|---|---|---|
| `--endpoint` | `http://localhost:8080/v1` | Base URL of the agent's OpenAI-compatible API |
| `--pipeline` | `answer_quality.yaml` | Pipeline YAML filename from `user_pipelines/` |
| `--dataset` | `user_datasets/sample_answer_quality.json` | Path to test case JSON file |
| `--dry-run` | | Validate inputs and print what would run, without executing |
