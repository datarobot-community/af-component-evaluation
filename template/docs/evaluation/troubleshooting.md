# Troubleshooting

User-facing gotchas when running evaluations. (Component developers: the full
running log of known issues lives in the repo's `BUGS.md`.)

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

## Bedrock / Claude can't be the stock judge

NeMo's built-in judge client always sends **both** `temperature` and `top_p`. The
DR gateway's **Bedrock** models (e.g. `bedrock/anthropic.claude-sonnet-4-6`) reject
that combination:

```
400 "`temperature` and `top_p` cannot both be specified for this model.
     Please use only one."
```

**Workaround:** use an **Azure** GPT judge model (`azure/gpt-5-5-2026-04-23`) —
Azure/OpenAI models accept both params, so the stock judge works unmodified. Set it
via the pipeline's `judge.model_id` or the `JUDGE_MODEL_ID` env var.

If you specifically need Claude as judge, write a small custom judge call in your
scorer that sends only `temperature` (BYOB scorers are arbitrary Python and can
reuse NeMo's judge templates).

## Adversarial prompts can content-filter the judge

When judging `safety_refusal` or `prompt_injection` cases, the DR gateway's
content filter can return a deterministic `400` on the adversarial text itself —
either the attack *question* embedded in the judge prompt, or a long agent
*response* about jailbreaks. Because it's deterministic, retries don't help and
`judge_score()` returns `CALL_ERROR`.

This is a **judge-side** failure, not an agent failure. The component treats it as
[inconclusive](./outputs.md): the case gets `score: null` / `passed: null`
and is excluded from rates instead of dragging down the pass rate. The summary
reports it under `inconclusive_cases`.

To actually score such cases, consider judging primarily the *response* (not
re-sending the raw adversarial question into the judge prompt), or route safety
judging to a model/endpoint without an aggressive input filter.
