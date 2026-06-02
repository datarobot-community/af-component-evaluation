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
"""EXAMPLE: How to write a judge-free (deterministic) benchmark.

This file is a teaching template — copy it, rename it, and adapt
``evaluate_response()`` to score whatever YOUR agent needs to produce.
See also ``user_example_benchmark_judge_based.py`` for the judge pattern.

------------------------------------------------------------------
Key concepts
------------------------------------------------------------------
1.  ``@benchmark(name=..., dataset=..., prompt=..., endpoint_type=...)``
    Declares this file as a NeMo BYOB benchmark.  ``name`` must match
    ``benchmark.name`` in your pipeline YAML.  ``prompt`` is a Python
    format-string rendered per case from the dataset row's fields —
    that rendered string is what gets *sent to the agent*.  ``dataset``
    is always ``"cases.jsonl"`` (a placeholder; the real file is
    supplied via ``--dataset`` at runtime).

2.  ``@scorer``
    Marks the decorated function as the scoring function.  NeMo calls
    it once per case with a ``ScorerInput`` carrying:
      ``sample.response``   — the agent's raw text reply
      ``sample.metadata``   — the full dataset row as a ``dict``
    Return a ``dict`` of named numeric scores.  Omit the numeric key
    entirely to mark a case as *inconclusive* (not a failure).

3.  ``evaluate_response(response, metadata)`` — pure helper
    Separating the logic into a standalone function lets unit tests
    import and call it directly, with no NeMo fixtures needed.
    See ``tests/test_benchmarks.py`` for the pattern.

4.  No judge = no HTTP calls, no credentials, fully reproducible.
    Every run of the same dataset returns identical scores.
    Contrast with ``user_example_benchmark_judge_based.py``.
------------------------------------------------------------------

What this example demonstrates
------------------------------------------------------------------
Keyword presence — checks that the agent's response contains every
required keyword.  Useful for: required disclaimers, brand phrases,
structural markers in structured output.

Dataset fields (add to your user_datasets/*.json cases):
  input              (required) the prompt sent to the agent
  required_keywords  (required) list of strings that MUST appear
  case_sensitive     (optional) default ``false``

Example dataset case::

    {
        "input": "Summarize our refund policy.",
        "required_keywords": ["30 days", "receipt"],
        "case_sensitive": false
    }
"""

from typing import Any

from nemo_evaluator.contrib.byob import ScorerInput, benchmark, scorer

# ---------------------------------------------------------------------------
# Step 1 — write the pure scoring logic.
# ---------------------------------------------------------------------------


def evaluate_response(response: str, metadata: dict[str, Any]) -> dict[str, Any]:
    """Deterministic keyword check — no I/O, importable in unit tests.

    Usage in tests::

        from user_pipelines.user_example_benchmark_judge_free import evaluate_response
        result = evaluate_response("30-day returns with receipt.", {"required_keywords": ["30", "receipt"]})
        assert result["score"] == 1.0
    """
    keywords = metadata.get("required_keywords")
    if not keywords:
        # No numeric key → evaluator marks this case inconclusive, not failed.
        return {"reason": "no required_keywords provided — skipping case"}

    case_sensitive = bool(metadata.get("case_sensitive", False))
    text = response if case_sensitive else response.lower()

    missing = [
        kw for kw in keywords if (kw if case_sensitive else kw.lower()) not in text
    ]

    if missing:
        return {
            "score": 0.0,
            "keyword_presence": 0.0,
            "reason": f"missing keywords: {missing}",
        }
    return {
        "score": 1.0,
        "keyword_presence": 1.0,
        "reason": "all required keywords present",
    }


# ---------------------------------------------------------------------------
# Step 2 — wire it up with @benchmark + @scorer.
# ---------------------------------------------------------------------------


@benchmark(  # type: ignore[untyped-decorator]
    name="keyword_presence",  # must match benchmark.name in your pipeline YAML
    dataset="cases.jsonl",  # placeholder — overridden by --dataset at runtime
    # `prompt` is what NeMo sends to the agent.  Fields in {braces} are filled
    # from the dataset row.  Add extra fields here if the agent needs more
    # context, e.g.: "{input}\n\nContext:\n{context}"
    prompt="{input}",
    endpoint_type="chat",  # "chat" for chat-completion agents (the common case)
)
@scorer  # type: ignore[untyped-decorator]
def score(sample: ScorerInput) -> dict[str, Any]:
    return evaluate_response(sample.response, sample.metadata)
