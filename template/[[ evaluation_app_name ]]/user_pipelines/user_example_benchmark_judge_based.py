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
"""EXAMPLE: a judge-based benchmark — copy, rename, and adapt.

Demonstrates custom-criteria scoring: each dataset case carries its own grading
instructions in a ``criteria`` field, which the judge folds into its prompt — so
one benchmark file can cover many qualitative checks. See
``user_example_benchmark_judge_free.py`` for the simpler no-judge pattern (prefer
it when you have deterministic success criteria).

Dataset fields:
  input     (required) the prompt sent to the agent
  criteria  (optional) extra grading instructions injected into the judge;
            blank → the template's default rubric

Full guide — judge config, judge_score templates, handling CALL_ERROR/PARSE_ERROR
as inconclusive, the required pipeline judge: block:
docs/evaluation/writing-benchmarks.md
"""

import os
from typing import Any

from nemo_evaluator.contrib.byob import ScorerInput, benchmark, scorer

# Import judge_score from evaluator.judge (not directly from nemo_evaluator): it
# wraps NeMo's judge to drop the redundant top_p that Anthropic/Bedrock judges
# reject. Use this import in your own judge-based benchmarks too.
from evaluator.judge import judge_score

# JUDGE_* env vars are exported by run.py from the pipeline's judge: block; the
# defaults here are fallbacks for direct/manual invocation. api_key is an env var
# *name* (resolved to a Bearer token at call time), not the token value.
JUDGE = {
    "url": os.environ.get("JUDGE_URL", "https://app.datarobot.com/api/v2/genai/llmgw"),
    "model_id": os.environ.get("JUDGE_MODEL_ID", "azure/gpt-5-5-2026-04-23"),
    "api_key": os.environ.get("JUDGE_API_KEY_NAME", "DATAROBOT_API_TOKEN"),
    "temperature": 0.0,
    "max_new_tokens": 1024,
}

# judge_score() returns one of these strings when the LLM call itself failed
# (network error, HTTP 4xx/5xx after retries) or its output couldn't be parsed.
# Treat those as inconclusive — missing numeric key → aggregation skips the case.
_JUDGE_ERROR_GRADES = frozenset({"CALL_ERROR", "PARSE_ERROR"})


def _scored(result: dict[str, Any], category_key: str) -> dict[str, Any]:
    """Shape a raw judge result into the scores dict NeMo expects.

    On a judge error: no numeric key → evaluator marks the case inconclusive.
    On a valid grade: emit ``score``, ``<category_key>``, and ``judge_grade``.
    """
    grade = result["judge_grade"]
    if grade in _JUDGE_ERROR_GRADES:
        return {"judge_grade": grade}
    score = result["judge_score"]
    return {"score": score, category_key: score, "judge_grade": grade}


@benchmark(  # type: ignore[untyped-decorator]
    name="custom_criteria",  # must match benchmark.name in your pipeline YAML
    dataset="cases.jsonl",  # placeholder — overridden by --dataset at runtime
    prompt="{input}",
    endpoint_type="chat",
    extra={"judge": JUDGE},  # forwarded to the runner so the scorer can reach the judge
)
@scorer  # type: ignore[untyped-decorator]
def score(sample: ScorerInput) -> dict[str, Any]:
    """Likert-5 quality judge using per-case custom grading criteria."""
    question = sample.metadata.get("input", "")
    # Per-case grading instructions; blank → the template's default rubric.
    criteria = sample.metadata.get("criteria", "")
    result = judge_score(
        sample, template="likert_5", question=question, criteria=criteria
    )
    return _scored(result, "quality")
