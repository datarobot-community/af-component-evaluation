# Troubleshooting

User-facing gotchas when running evaluations.

## Judge model names are catalog names, not LiteLLM names

NeMo makes plain OpenAI-compatible HTTP calls. There is **no LiteLLM layer** on the judge path. The `datarobot/...` prefix is a LiteLLM routing convention and only works behind a LiteLLM proxy. Whatever endpoint you name in the pipeline receives the `model` string verbatim.

Against the DR LLM gateway directly, use the **gateway catalog name** with no `datarobot/` prefix&mdash;for example `azure/gpt-5-5-2026-04-23`. List available models:

```bash
curl -s -H "Authorization: Bearer $DATAROBOT_API_TOKEN" \
  "$DATAROBOT_ENDPOINT/api/v2/genai/llmgw/models"
```

## Judge parameters cannot be customized per model

NeMo's built-in judge client sends a fixed sampling parameter set that always includes **both** `temperature` and `top_p`, and the harness gives you no way to override it. Some model APIs accept only one of the two and reject the request when both are present, which rules those models out as the stock judge. Claude models via `bedrock/...` are the case you are most likely to hit:

```
400 "`temperature` and `top_p` cannot both be specified for this model.
     Please use only one."
```

**Workaround**: Use an **Azure** GPT judge model (`azure/gpt-5-5-2026-04-23`). Azure and OpenAI models accept both parameters, so the stock judge works unmodified. Set `judge.model_id` in the pipeline YAML or use the `JUDGE_MODEL_ID` environment variable.

If you specifically need Claude as judge, write a custom judge call in your scorer that sends only `temperature`. BYOB scorers are arbitrary Python and can reuse NeMo's judge templates.

## Adversarial prompts can content-filter the judge

When judging adversarial cases in judge-based benchmarks such as `safety_refusal`, some model endpoints apply input content filtering that can reject the adversarial text and return a `400`. In that case `judge_score()` returns `CALL_ERROR`.

This is a **judge-side** failure, not an agent failure. The component treats it as [inconclusive](./outputs.md): the case gets `score: null` and `passed: null`, and is excluded from rates instead of dragging down the pass rate. The summary reports it under `inconclusive_cases`.

## Agent endpoint unreachable

If validation fails with an unreachable endpoint error:

1. Confirm the agent is running (for local dev, `dr run dev` typically serves `http://localhost:8842/v1`).
2. Run `task eval -- --endpoint ... --pipeline ... --dry-run` to validate without scoring.
3. Set `AGENT_API_KEY` only when the agent requires authentication. Local DRUM agents usually need none.

## Task namespace not found

If `dr task run evaluations:eval` fails with a task-not-found error:

```bash
dr task compose && task --list
```

Pick the `<namespace>:eval` entry from the list. The namespace matches `evaluation_app_name` from Copier setup (default `evaluations`).

## See also

- [Outputs](./outputs.md)&mdash;inconclusive cases and exit codes.
- [Pipelines](./pipelines.md)&mdash;judge block and model naming rules.
