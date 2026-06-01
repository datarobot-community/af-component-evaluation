# Example Run

`run.py` is invoked by the external CLI with flags. This documents what those flags correspond to.

## Usage

```sh
python run.py \
  --endpoint  http://localhost:8080/v1 \
  --pipeline  agent_quality_safety.yaml \
  --dataset   user_datasets/sample_cases.json
```

## Required environment variables

| Variable | Description |
|---|---|
| `AGENT_API_KEY` | API key for the agent endpoint |
| `AGENT_MODEL_NAME` | Model name the agent endpoint expects |
| `JUDGE_API_KEY` | API key for the judge LLM |

The judge model and URL are set in the pipeline YAML, not here.

## Optional environment variables

| Variable | Default | Description |
|---|---|---|
| `MAX_CONCURRENCY` | `4` | Parallel requests to the agent |

## Arguments

| Flag | Example | Description |
|---|---|---|
| `--endpoint` | `http://localhost:8080/v1` | Base URL of the agent's OpenAI-compatible API |
| `--pipeline` | `agent_quality_safety.yaml` | Pipeline YAML filename from `pipelines/` |
| `--dataset` | `user_datasets/sample_cases.json` | Path to test case JSON file |
| `--dry-run` | | Validate inputs and print what would run, without executing |
