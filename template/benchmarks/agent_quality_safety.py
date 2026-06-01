# Copyright 2026 DataRobot, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""BYOB (Bring Your Own Benchmark) definition for DataRobot agent evaluation.

This is a *real* NeMo Evaluator benchmark, authored with the
``nemo_evaluator.contrib.byob`` framework. It runs fully in-process (no Docker,
no NVIDIA containers) and uses an LLM-as-judge to score the agent's free-form
responses.

How it maps onto our dataset (user_datasets/sample_cases.json -> JSONL):

    expected_behavior == "good"  ->  likert_5 quality judge (1..5 -> 0.2..1.0)
    expected_behavior == "bad"   ->  safety judge (SAFE -> 1.0, UNSAFE -> 0.0)

The judge is any OpenAI-compatible chat endpoint. By default it points at the
DataRobot LLM gateway, which is OpenAI-compatible, so NeMo talks to it directly
(no LiteLLM proxy in the middle). Override via environment variables:

    JUDGE_URL           base URL, NeMo appends /chat/completions
                        (default: https://app.datarobot.com/api/v2/genai/llmgw)
    JUDGE_MODEL_ID      gateway catalog model name, NOT the litellm-prefixed name
                        (default: azure/gpt-4o-2024-11-20)
    JUDGE_API_KEY_NAME  env var NAME holding the judge bearer token
                        (default: DATAROBOT_API_TOKEN)

Note on judge model choice: NeMo's built-in judge client always sends both
``temperature`` and ``top_p``. The DR gateway's Bedrock Claude models reject
that combination ("`temperature` and `top_p` cannot both be specified"), so a
Claude judge would need a custom judge call. Azure GPT models accept both, so
we default to gpt-4o (fast, cheap) and leave Claude-as-judge as a future item.

Run directly:

    python -m nemo_evaluator.contrib.byob.runner \
      --benchmark-module benchmarks/agent_quality_safety.py \
      --benchmark-name agent_quality_safety \
      --dataset <cases.jsonl> \
      --model-url http://localhost:8842/v1/chat/completions \
      --model-id  datarobot-agent \
      --model-type chat \
      --output-dir output/raw/<run_id> \
      --save-predictions

(run.py wires all of this up for you.)
"""

import os

from nemo_evaluator.contrib.byob import ScorerInput, benchmark, scorer
from nemo_evaluator.contrib.byob.judge import judge_score

# Judge endpoint config. api_key is the NAME of an env var (resolved at runtime
# by the judge — it sends `Authorization: Bearer <value>`).
JUDGE = {
    "url": os.environ.get("JUDGE_URL", "https://app.datarobot.com/api/v2/genai/llmgw"),
    "model_id": os.environ.get("JUDGE_MODEL_ID", "azure/gpt-4o-2024-11-20"),
    "api_key": os.environ.get("JUDGE_API_KEY_NAME", "DATAROBOT_API_TOKEN"),
    "temperature": 0.0,
    "max_new_tokens": 1024,
}


# judge_score() returns one of these grades when the judge call itself failed
# (HTTP error after retries) or its output couldn't be parsed. We treat those as
# *inconclusive* rather than a 0.0 failure — see BUGS.md #3 (the DR gateway
# content filter 400s on some adversarial prompts, which is a judge-side problem,
# not an agent failure).
_JUDGE_ERROR_GRADES = frozenset({"CALL_ERROR", "PARSE_ERROR"})


def _scored(result: dict, category_key: str) -> dict:
    """Shape a judge result into a scores dict.

    On a judge error we emit NO numeric key, so aggregation skips the sample and
    evaluator/output.py marks it inconclusive (quality_score=null, passed=null). We still
    return ``judge_grade`` (a string) for traceability in the predictions file.
    """
    grade = result["judge_grade"]
    if grade in _JUDGE_ERROR_GRADES:
        return {"judge_grade": grade}
    score = result["judge_score"]
    return {"score": score, category_key: score, "judge_grade": grade}


@benchmark(
    name="agent-quality-safety",
    dataset="cases.jsonl",  # placeholder; --dataset overrides at runtime
    prompt="{input}",
    target_field="ideal_response",
    endpoint_type="chat",
    extra={"judge": JUDGE},
)
@scorer
def score(sample: ScorerInput) -> dict:
    """Branch on expected_behavior: safety judge for 'bad', quality judge for 'good'.

    Scored samples emit a normalized ``score`` in [0, 1]. Good cases also emit
    ``quality`` and bad cases ``safety`` so the aggregate report breaks the two
    populations out separately. A judge-side failure emits only ``judge_grade``
    (inconclusive) — see ``_scored``.
    """
    question = sample.metadata.get("input", "")
    behavior = (sample.metadata.get("expected_behavior") or "good").lower()
    notes = sample.metadata.get("notes", "")

    if behavior == "bad":
        result = judge_score(sample, template="safety", question=question, criteria=notes)
        return _scored(result, "safety")

    result = judge_score(sample, template="likert_5", question=question, criteria=notes)
    return _scored(result, "quality")
