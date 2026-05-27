# NeMo Evaluator Pipeline Configs

This directory contains YAML files in **NeMo Evaluator's native format** — the schema that
`nemo-evaluator-launcher` actually reads. These are distinct from the higher-level run configs
in `configs/` (which are our schema) and the JSON contracts in `schemas/`.

## Three-Layer Contract

```
User / CLI / React
        │
        ▼
configs/example_run.yaml          ← OUR schema (schemas/input_schema.json)
        │
        ▼  run_eval.py translates this into NeMo format, substituting env vars
        │
        ▼
pipelines/<name>.yaml             ← NEMO's schema (Hydra-based, this directory)
        │
        ▼  nemo-evaluator-launcher runs this, writes to <output_dir>/artifacts/
        │
        ▼
<output_dir>/artifacts/           ← NeMo raw output
        │
        ▼  run_eval.py normalizes this into our output schema
        │
        ▼
<output_dir>/eval_results.json    ← OUR schema (schemas/output_schema.json)
```

## NeMo YAML Format

NeMo Evaluator uses [Hydra](https://hydra.cc/) config composition. Every pipeline YAML has:

```yaml
defaults:
  - execution: local        # local | lepton | slurm
  - deployment: none        # none | vllm | nim | sglang | trtllm | generic
  - _self_

execution:
  output_dir: <path>

target:
  api_endpoint:
    model_id: <string>       # model identifier the endpoint expects
    url: <string>            # full endpoint URL including /chat/completions
    api_key_name: <ENV_VAR>  # NAME of the env var holding the API key (not the key itself)

evaluation:
  nemo_evaluator_config:
    config:
      params:
        parallelism: <int>
        request_timeout: <int>
  tasks:
    - name: <task_name>
      nemo_evaluator_config:
        config:
          params:
            extra:
              # task-specific parameters
```

## Key NeMo Conventions

- `api_key_name` is the **name of an environment variable**, not the key value itself.
  Example: `api_key_name: AGENT_API_KEY` means NeMo reads `$AGENT_API_KEY` at runtime.
- Task names are dot-separated benchmark identifiers: `lm-evaluation-harness.ifeval`,
  `simple_evals.gpqa_diamond`, etc. Use `nemo-evaluator-launcher ls tasks` to list all available.
- Custom datasets go under `extra.custom_dataset` with `path` and `format` (`openai` or `native`).
- LLM judge config goes under `extra.judge`.
- Output always lands in `<output_dir>/artifacts/` — specifically `results.json` for aggregate
  scores and `report.json` for per-sample request/response pairs (if enabled).

## Files in This Directory

| File | Purpose |
|---|---|
| `custom_qa_judge.yaml` | LLM-as-judge evaluation on a custom Q&A dataset |

## Customizing a Pipeline

Copy an existing pipeline file and adjust the `tasks` section. The `execution.output_dir`,
`target.api_endpoint.*`, and any `extra.*` values are filled in by `run_eval.py` at runtime —
do not hardcode secrets or paths in pipeline files committed to version control.
