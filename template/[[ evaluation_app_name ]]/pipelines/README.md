# Pipeline Configs

YAML files here describe an evaluation run in **our own simple schema** (not
NeMo's Hydra format). `run.py` reads the selected pipeline, exports the
judge config to the benchmark, and invokes the NeMo **BYOB** runner in-process.

> Historical note: an earlier design used `nemo-evaluator-launcher` with Hydra
> configs and a `custom_qa` task. That approach was abandoned — the launcher runs
> every task in an `nvcr.io` Docker container (`--gpus all`) and has no generic
> "custom Q&A + judge" task. We use NeMo BYOB instead (see top-level `README.md`).

## Schema

```yaml
benchmark:
  module: benchmarks/agent_quality_safety.py  # path (repo-relative) to the BYOB module
  name: agent_quality_safety                   # normalized benchmark name (matches @benchmark)

target:                                        # the agent under test
  model_type: chat                             # chat | completions | completions_logprob
  model_id: unknown                            # "model" string sent to the agent endpoint
  api_key_name: AGENT_API_KEY                  # env var NAME; only sent if that var is set

judge:                                         # LLM-as-judge endpoint (OpenAI-compatible)
  url: https://app.datarobot.com/api/v2/genai/llmgw   # base URL; NeMo appends /chat/completions
  model_id: azure/gpt-4o-2024-11-20            # gateway CATALOG name (NOT a litellm datarobot/ prefix)
  api_key_name: DATAROBOT_API_TOKEN            # env var NAME holding the judge bearer token

run:
  parallelism: 4
  max_tokens: 1024
  temperature: 0.0
  timeout_per_sample: 180
```

## Key conventions

- **Model names are endpoint-catalog names, not LiteLLM names.** NeMo makes plain
  OpenAI-compatible HTTP calls — there is no LiteLLM layer. Against the DR LLM
  gateway directly, use the catalog name with no `datarobot/` prefix (e.g.
  `azure/gpt-4o-2024-11-20`). List models: `GET .../genai/llmgw/models`.
- **`api_key_name` is an env var NAME**, not the key value. `DATAROBOT_API_TOKEN`
  for the judge; `AGENT_API_KEY` for the agent (optional — only sent if set).
- **`target.model_id: unknown`** is myagent.py's placeholder sentinel → the agent
  uses its own configured default LLM. Set a real model only if the agent's
  `get_llm()` understands it.
- ⚠️ **Bedrock/Claude can't be the stock judge** — NeMo's judge client sends both
  `temperature` and `top_p`, which DR-gateway Bedrock models reject. Use Azure
  GPT. See `the known issues notes #1`.

## Files

| File | Purpose |
|---|---|
| `agent_quality_safety.yaml` | LLM-as-judge: good cases → likert_5 quality, bad cases → safety |

## Adding a pipeline

Copy `agent_quality_safety.yaml`, point `benchmark.module`/`name` at your BYOB
benchmark (see `benchmarks/agent_quality_safety.py`), and set the judge model.
Built-in judge templates available to benchmarks: `binary_qa`, `binary_qa_partial`,
`likert_5`, `safety`.
