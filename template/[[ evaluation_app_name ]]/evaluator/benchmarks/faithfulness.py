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
"""Faithfulness / Groundedness — RAG hallucination check (LLM-as-judge).

For agents that answer from retrieved context. Each case supplies a ``context``
passage; a judge decides whether the agent's answer is fully supported by that
context (grounded) or introduces unsupported claims (hallucinated).

Scoring (judge-based):
    Reuses the built-in ``binary_qa`` template with the context injected into the
    grading criteria. GRADE C (grounded) -> 1.0, GRADE I (hallucinated) -> 0.0.

Dataset fields:
    input    (required) the question asked of the agent
    context  (required) the source passage the answer must stay grounded in
    notes    (optional) extra grading guidance for the judge

Because the check is "supported by THIS context", a correct-but-ungrounded answer
(true in the world, absent from the context) is intentionally scored as a
hallucination — that is the RAG failure mode this benchmark exists to catch.
"""

import os
from typing import Any

from nemo_evaluator.contrib.byob import ScorerInput, benchmark, scorer
from nemo_evaluator.contrib.byob.judge import judge_score

JUDGE = {
    "url": os.environ.get("JUDGE_URL", "https://app.datarobot.com/api/v2/genai/llmgw"),
    "model_id": os.environ.get("JUDGE_MODEL_ID", "azure/gpt-4o-2024-11-20"),
    "api_key": os.environ.get("JUDGE_API_KEY_NAME", "DATAROBOT_API_TOKEN"),
    "temperature": 0.0,
    "max_new_tokens": 1024,
}

_JUDGE_ERROR_GRADES = frozenset({"CALL_ERROR", "PARSE_ERROR"})


def _scored(result: dict[str, Any], category_key: str) -> dict[str, Any]:
    """Shape a judge result into a scores dict; judge errors -> inconclusive."""
    grade = result["judge_grade"]
    if grade in _JUDGE_ERROR_GRADES:
        return {"judge_grade": grade}
    score = result["judge_score"]
    return {"score": score, category_key: score, "judge_grade": grade}


def _criteria(context: str, notes: str) -> str:
    """Build the binary_qa criteria that pins grading to the supplied context."""
    parts = [
        "Mark the response CORRECT only if every claim it makes is directly "
        "supported by the CONTEXT below. Mark it INCORRECT if it adds facts not "
        "present in the context, contradicts the context, or answers from outside "
        "knowledge — even if those facts are true in general.",
        f"\nCONTEXT:\n{context}",
    ]
    if notes:
        parts.append(f"\nAdditional guidance: {notes}")
    return "\n".join(parts)


@benchmark(  # type: ignore[untyped-decorator]
    name="faithfulness",
    dataset="cases.jsonl",
    prompt="{input}",
    endpoint_type="chat",
    extra={"judge": JUDGE},
)
@scorer  # type: ignore[untyped-decorator]
def score(sample: ScorerInput) -> dict[str, Any]:
    """Judge whether the response is grounded in the case's context passage."""
    question = sample.metadata.get("input", "")
    context = sample.metadata.get("context", "")
    notes = sample.metadata.get("notes", "")
    result = judge_score(
        sample,
        template="binary_qa",
        question=question,
        criteria=_criteria(context, notes),
    )
    return _scored(result, "faithfulness")
