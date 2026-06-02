# Pipelines

A **pipeline** is a small YAML that wires a benchmark to the agent under test (and,
for judge-based benchmarks, to a judge model). `run.py` reads the selected
pipeline and invokes the NeMo **BYOB** runner in-process — no Docker, no GPUs.

The files here are **defaults, not examples**: pick the one that matches what you
want to measure, point `--dataset` at your own `user_datasets/*.json`, and run.
You only edit a pipeline if you want a different judge model or run settings.

```bash
task eval -- --endpoint http://localhost:8842/v1 \
  --pipeline answer_quality.yaml \
  --dataset user_datasets/sample_answer_quality.json
```

> Historical note: an earlier design used `nemo-evaluator-launcher` with Hydra
> configs and a `custom_qa` task. That was abandoned — the launcher runs every
> task in an `nvcr.io` Docker container (`--gpus all`) with no generic
> "custom Q&A + judge" task. We use NeMo BYOB instead (see top-level `README.md`).

## The 8 default benchmarks

Each benchmark is **isolated**: one case type, one scoring strategy. The
**Judge?** column tells you whether the pipeline needs a judge model — judge-free
ones are deterministic, reproducible, and run with no judge credentials.

| Pipeline | Judge? | Measures | Key dataset fields |
|---|:---:|---|---|
| `answer_quality.yaml` | ✅ judge | General response quality (Likert 1-5) | `input`, `notes` |
| `safety_refusal.yaml` | ✅ judge | Refuses harmful requests (SAFE/UNSAFE) | `input`, `notes` |
| `faithfulness.yaml` | ✅ judge | Answer grounded in a RAG `context` (no hallucination) | `input`, `context`, `notes` |
| `answer_correctness.yaml` | ⚙️ none | Matches a known answer (exact/normalized/contains) | `input`, `ideal_response`, `match_mode` |
| `instruction_following.yaml` | ⚙️ none | Obeys structural constraints (len, JSON, phrases, regex) | `input`, `constraints` |
| `prompt_injection.yaml` | ⚙️ none | Resists hijack — a `canary` must NOT appear | `input`, `canary` |
| `pii_leakage.yaml` | ⚙️ none | No PII in the response (regex detectors) | `input`, `entity_types` |
| `tool_grounding.yaml` | ⚙️ none | Used its tool/data — a `canary` MUST appear | `input`, `canary` |

Each has a matching `user_datasets/sample_<name>.json` showing the required shape.

## Schema

```yaml
benchmark:
  module: evaluator/benchmarks/answer_quality.py  # repo-relative path to the BYOB module
  name: answer_quality                            # normalized benchmark name (matches @benchmark)

target:                                           # the agent under test
  model_type: chat                                # chat | completions | completions_logprob
  model_id: unknown                               # "model" string sent to the agent endpoint
  api_key_name: AGENT_API_KEY                     # env var NAME; only sent if that var is set

judge:                                            # OMIT ENTIRELY for judge-free benchmarks
  url: https://app.datarobot.com/api/v2/genai/llmgw   # base URL; NeMo appends /chat/completions
  model_id: azure/gpt-4o-2024-11-20               # gateway CATALOG name (NOT a litellm datarobot/ prefix)
  api_key_name: DATAROBOT_API_TOKEN               # env var NAME holding the judge bearer token

run:
  parallelism: 4
  max_tokens: 1024
  temperature: 0.0
  timeout_per_sample: 180
```

## Key conventions

- **Judge-free pipelines omit the `judge:` block entirely.** `run.py` exports judge
  credentials only when the block is present; the benchmark never makes a judge
  call. (The UI also reads this to show whether a run needs a judge model.)
- **Model names are endpoint-catalog names, not LiteLLM names.** NeMo makes plain
  OpenAI-compatible HTTP calls — no LiteLLM layer. Against the DR LLM gateway, use
  the catalog name with no `datarobot/` prefix (e.g. `azure/gpt-4o-2024-11-20`).
  List models: `GET .../genai/llmgw/models`.
- **`api_key_name` is an env var NAME**, not the key value. `DATAROBOT_API_TOKEN`
  for the judge; `AGENT_API_KEY` for the agent (optional — only sent if set).
- **`target.model_id: unknown`** is the agent's placeholder sentinel → the agent
  uses its own configured default LLM. Set a real model only if the agent's
  `get_llm()` understands it.
- ⚠️ **Bedrock/Claude can't be the stock judge** — NeMo's judge client sends both
  `temperature` and `top_p`, which DR-gateway Bedrock models reject. Use Azure
  GPT. See `the known issues notes #1`.

## Writing your own benchmark + pipeline

Copy the closest default benchmark from `evaluator/benchmarks/` (each file is
self-contained — no shared imports to untangle), adjust its `@benchmark`/`@scorer`,
then copy the matching pipeline here and repoint `benchmark.module`/`name`.
Built-in judge templates available to benchmarks: `binary_qa`, `binary_qa_partial`,
`likert_5`, `safety` — or pass a custom template string + `grade_pattern` /
`score_mapping` to `judge_score()`.
