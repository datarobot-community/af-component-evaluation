# Pipelines

A **pipeline** is a small YAML file that wires a benchmark to the agent under test (and, for judge-based benchmarks, to a judge model). `run.py` reads the selected pipeline and invokes the NeMo **BYOB** runner in-process&mdash;no Docker and no GPUs.

The files in `user_pipelines/` are **defaults, not examples**. Pick the one that matches what you want to measure, point `--dataset` at your own `user_datasets/*.json`, and run. Edit a pipeline only when you need a different judge model or run settings.

```bash
task eval -- \
  --endpoint http://localhost:8842/v1 \
  --pipeline answer_quality.yaml \
  --dataset  user_datasets/sample_answer_quality.json
```

## The 8 default benchmarks

Each benchmark is **isolated**: one case type and one scoring strategy. The **Judge?** column tells you whether the pipeline needs a judge model. Judge-free benchmarks are deterministic, reproducible, and run with no judge credentials. See [Benchmarks](./benchmarks.md) for full details on each.

| Pipeline | Judge? | Measures | Key dataset fields |
|---|---|---|---|
| `answer_quality.yaml` | Yes | General response quality (Likert 1–5). | `input`, `notes`. |
| `safety_refusal.yaml` | Yes | Refuses harmful requests (SAFE/UNSAFE). | `input`, `notes`. |
| `faithfulness.yaml` | Yes | Answer grounded in a RAG `context` (no hallucination). | `input`, `context`, `notes`. |
| `answer_correctness.yaml` | No | Matches a known answer (exact/normalized/contains). | `input`, `ideal_response`, `match_mode`. |
| `instruction_following.yaml` | No | Obeys structural constraints (length, JSON, phrases, regex). | `input`, `constraints`. |
| `prompt_injection.yaml` | No | Resists hijack&mdash;a `canary` must NOT appear. | `input`, `canary`. |
| `pii_leakage.yaml` | No | No PII in the response (regex detectors). | `input`, `entity_types`. |
| `tool_grounding.yaml` | No | Used its tool/data&mdash;a `canary` MUST appear. | `input`, `canary`. |

Each pipeline has a matching `user_datasets/sample_<name>.json` that shows the required shape.

## Schema

A pipeline YAML has four top-level blocks. Omit `judge` entirely for judge-free benchmarks.

```yaml
benchmark:
  module: datarobot_genai/eval/benchmarks/answer_quality.py  # Built-in path from datarobot-genai[eval]; a local repo-relative path also works for custom benchmarks.
  name: answer_quality                            # Normalized benchmark name (matches @benchmark).

target:                                           # The agent under test.
  model_type: chat                                # chat | completions | completions_logprob
  model_id: unknown                               # Model string sent to the agent endpoint.
  api_key_name: AGENT_API_KEY                     # Env var NAME; only sent if that var is set.

judge:                                            # OMIT ENTIRELY for judge-free benchmarks.
  url: https://app.datarobot.com/api/v2/genai/llmgw   # Base URL; NeMo appends /chat/completions.
  model_id: azure/gpt-5-5-2026-04-23               # Gateway CATALOG name (NOT a LiteLLM datarobot/ prefix).
  api_key_name: DATAROBOT_API_TOKEN               # Env var NAME holding the judge bearer token.

run:
  parallelism: 4
  max_tokens: 1024
  temperature: 0.0
  timeout_per_sample: 180
```

## Key conventions

- **Judge-free pipelines omit the `judge:` block entirely.** `run.py` exports judge credentials only when the block is present; the benchmark never makes a judge call. The UI also reads this to show whether a run needs a judge model.
- **Model names are endpoint-catalog names, not LiteLLM names.** NeMo makes plain OpenAI-compatible HTTP calls with no LiteLLM layer. Against the DR LLM gateway, use the catalog name with no `datarobot/` prefix (for example `azure/gpt-5-5-2026-04-23`). List models with `GET https://app.datarobot.com/api/v2/genai/llmgw/models`.
- **`api_key_name` is an env var NAME**, not the key value. Use `DATAROBOT_API_TOKEN` for the judge and `AGENT_API_KEY` for the agent (optional&mdash;only sent if set).
- **`target.model_id: unknown`** is the agent placeholder sentinel. The agent uses its own configured default LLM. Set a real model only if the agent `get_llm()` method understands it.
- **Note**: Bedrock/Claude cannot be the stock judge. NeMo judge client sends both `temperature` and `top_p`, which DR-gateway Bedrock models reject. Use an Azure GPT model. See [Troubleshooting](./troubleshooting.md).

## Writing your own

To author a custom benchmark and pipeline (judge-based or judge-free), copy one of the annotated `user_example_*` templates in `user_pipelines/`. See [Writing your own benchmark](./writing-benchmarks.md) for the full guide.

## See also

- [Benchmarks](./benchmarks.md)&mdash;what each built-in benchmark measures and how it scores.
- [Datasets](./datasets.md)&mdash;per-benchmark field requirements.
- [Troubleshooting](./troubleshooting.md)&mdash;judge model names and Bedrock limitations.
