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
"""EXAMPLE: How to write a judge-based benchmark.

This file is a teaching template — copy it, rename it, and adapt the
``@benchmark``/``@scorer`` to score what YOUR agent needs to produce.
See also ``user_example_benchmark_judge_free.py`` for the no-judge pattern
(simpler, no credentials required, fully reproducible — prefer it when you
have deterministic success criteria).

------------------------------------------------------------------
Key concepts
------------------------------------------------------------------
1.  Judge config (the ``JUDGE`` dict)
    Read from env vars so the same module works whether invoked via
    ``task eval`` (where ``run.py`` exports ``JUDGE_*`` from the pipeline's
    ``judge:`` block) or called manually for debugging (with env vars set
    directly in the shell).

2.  ``judge_score(sample, template=..., question=..., criteria=...)``
    Makes a single LLM call against the judge endpoint.  Built-in templates:
      ``likert_5``         — 1-5 quality/helpfulness score (→ 0.2..1.0)
      ``binary_qa``        — PASS / FAIL
      ``binary_qa_partial`` — PASS / PARTIAL / FAIL
      ``safety``           — SAFE / UNSAFE
    Pass ``template=<your_string>`` + ``grade_pattern`` + ``score_mapping``
    to supply a fully custom judge prompt.

3.  Error grades ``CALL_ERROR`` / ``PARSE_ERROR``
    Emitting no numeric score for these makes the evaluator mark the case
    *inconclusive* instead of failing it — the right default when the judge
    itself is broken or rate-limited, not when the agent answered poorly.

4.  The pipeline YAML **must** include a ``judge:`` block.
    ``run.py`` exports ``JUDGE_URL``, ``JUDGE_MODEL_ID``, and ``JUDGE_API_KEY_NAME``
    from that block before invoking the NeMo runner.  Judge-free benchmarks
    simply omit the block (and never call ``judge_score``).
------------------------------------------------------------------

What this example demonstrates
------------------------------------------------------------------
Custom-criteria scoring — each dataset case carries its own grading
instructions in a ``criteria`` field, which the judge incorporates into
its prompt.  This pattern lets one benchmark file cover many different
qualitative checks without hardcoding the criteria.

Dataset fields (add to your user_datasets/*.json cases):
  input     (required) the prompt sent to the agent
  criteria  (optional) extra grading instructions injected into the judge;
            leave blank to fall back to the template's default instructions

Example dataset case::

    {
        "input": "Explain compound interest to a 10-year-old.",
        "criteria": "The explanation must use an analogy and avoid jargon."
    }
"""

import os
from typing import Any

from nemo_evaluator.contrib.byob import ScorerInput, benchmark, scorer
from nemo_evaluator.contrib.byob.judge import judge_score

# ---------------------------------------------------------------------------
# Step 1 — configure the judge.
# ---------------------------------------------------------------------------

# JUDGE_* env vars are exported by run.py from the pipeline's judge: block.
# The defaults here are fallbacks for direct/manual invocation only.
JUDGE = {
    "url": os.environ.get("JUDGE_URL", "https://app.datarobot.com/api/v2/genai/llmgw"),
    "model_id": os.environ.get("JUDGE_MODEL_ID", "azure/gpt-4o-2024-11-20"),
    # api_key is an env var *name* — the judge resolves it to a Bearer token at
    # call time.  Do NOT put the token value here.
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


# ---------------------------------------------------------------------------
# Step 2 — wire it up with @benchmark + @scorer.
# ---------------------------------------------------------------------------


@benchmark(  # type: ignore[untyped-decorator]
    name="custom_criteria",  # must match benchmark.name in your pipeline YAML
    dataset="cases.jsonl",  # placeholder — overridden by --dataset at runtime
    prompt="{input}",
    endpoint_type="chat",
    # The judge dict is forwarded to the NeMo runner so it can reach the judge
    # endpoint when executing judge_score() calls inside the scorer.
    extra={"judge": JUDGE},
)
@scorer  # type: ignore[untyped-decorator]
def score(sample: ScorerInput) -> dict[str, Any]:
    """Likert-5 quality judge using per-case custom grading criteria."""
    question = sample.metadata.get("input", "")
    # Each case can carry its own grading instructions — more flexible than
    # hard-coding them here.  Leave `criteria` empty in the dataset to fall
    # back to the template's default "helpfulness / coherence / relevance" rubric.
    criteria = sample.metadata.get("criteria", "")
    result = judge_score(
        sample, template="likert_5", question=question, criteria=criteria
    )
    return _scored(result, "quality")
