# Troubleshooting

User-facing gotchas when running evaluations.

## Judge model names are catalog names, not LiteLLM names

NeMo makes plain OpenAI-compatible HTTP calls — there is **no LiteLLM layer**. The
`datarobot/...` prefix is a LiteLLM routing convention and only works behind a
LiteLLM proxy. Whatever endpoint you name in the pipeline receives the `model`
string verbatim.

Against the DR LLM gateway directly, use the **gateway catalog name** with no
`datarobot/` prefix — e.g. `azure/gpt-5-5-2026-04-23`. List available models:

```bash
GET https://app.datarobot.com/api/v2/genai/llmgw/models
```

## Judge parameters can't be customized per model

NeMo's built-in judge client sends a fixed sampling parameter set that always
includes **both** `temperature` and `top_p`, and the harness gives you no way to
override it. Some model APIs accept only one of the two and reject the request
when both are present, which rules those models out as the stock judge. Claude
models via `bedrock/...` are the case you are most likely to hit.

**Workaround:** use an **Azure** GPT judge model (`azure/gpt-5-5-2026-04-23`) —
Azure/OpenAI models accept both params, so the stock judge works unmodified. Set it
via the pipeline's `judge.model_id` or the `JUDGE_MODEL_ID` env var.

If you specifically need Claude as judge, write a small custom judge call in your
scorer that sends only `temperature` (BYOB scorers are arbitrary Python and can
reuse NeMo's judge templates).

## Adversarial prompts can content-filter the judge

When judging `safety_refusal` or `prompt_injection` cases, some model endpoints
apply input content filtering that can reject the adversarial text and return a
`400`, in which case `judge_score()` returns `CALL_ERROR`.

This is a **judge-side** failure, not an agent failure. The component treats it as
[inconclusive](./outputs.md): the case gets `score: null` / `passed: null`
and is excluded from rates instead of dragging down the pass rate. The summary
reports it under `inconclusive_cases`.
