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
"""EXAMPLE: a judge-free (deterministic) benchmark — copy, rename, and adapt.

Demonstrates a keyword-presence check: the response must contain every required
keyword. No judge means no HTTP calls, no credentials, and fully reproducible
scores. See ``user_example_benchmark_judge_based.py`` for the judge pattern.

Dataset fields:
  input              (required) the prompt sent to the agent
  required_keywords  (required) list of strings that MUST appear
  case_sensitive     (optional) default ``false``

Full guide — @benchmark/@scorer mechanics, inconclusive results, testing the
pure helper: docs/evaluation/writing-benchmarks.md
"""

from typing import Any

from nemo_evaluator.contrib.byob import ScorerInput, benchmark, scorer


def evaluate_response(response: str, metadata: dict[str, Any]) -> dict[str, Any]:
    """Deterministic keyword check — no I/O, importable in unit tests."""
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


@benchmark(  # type: ignore[untyped-decorator]
    name="keyword_presence",  # must match benchmark.name in your pipeline YAML
    dataset="cases.jsonl",  # placeholder — overridden by --dataset at runtime
    prompt="{input}",  # sent to the agent; {braces} filled from the dataset row
    endpoint_type="chat",
)
@scorer  # type: ignore[untyped-decorator]
def score(sample: ScorerInput) -> dict[str, Any]:
    return evaluate_response(sample.response, sample.metadata)
