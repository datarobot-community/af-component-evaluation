#!/usr/bin/env python3
"""
Pretty-print a normalized eval_results.json from a completed run.

Usage:
    python scripts/summarize_results.py results/20250526_143022/
    python scripts/summarize_results.py results/20250526_143022/eval_results.json
"""

import json
import sys
from pathlib import Path


def find_results(path: Path) -> Path:
    if path.is_file():
        return path
    candidate = path / "eval_results.json"
    if candidate.exists():
        return candidate
    raise FileNotFoundError(f"No eval_results.json found in {path}")


def summarize(results_path: Path):
    data = json.loads(results_path.read_text())

    print(f"\nRun ID:    {data.get('run_id', '?')}")
    print(f"Completed: {data.get('completed_at', '?')}")
    print(f"Agent:     {data.get('agent_endpoint', '?')}")
    print(f"Pipeline:  {data.get('pipeline', '?')}")
    print(f"Cases:     {data.get('total_cases', '?')}")

    s = data.get("summary", {})
    print(f"\nSummary")
    print(f"  Mean quality score : {s.get('mean_quality_score')}")
    print(f"  Pass rate          : {s.get('pass_rate')}")
    print(f"  Good case pass     : {s.get('good_case_pass_rate')}")
    print(f"  Bad case pass      : {s.get('bad_case_pass_rate')}")

    nemo_agg = s.get("nemo_aggregate", {})
    if nemo_agg:
        print(f"\nNeMo Aggregate Metrics")
        for key, value in nemo_agg.items():
            print(f"  {key}: {value}")

    cases = data.get("cases", [])
    if cases:
        print(f"\nPer-case Results")
        print(f"  {'ID':<15} {'Expect':<8} {'Score':<7} {'Pass':<6} Reason")
        print(f"  {'-'*15} {'-'*8} {'-'*7} {'-'*6} {'-'*45}")
        for c in cases:
            score = c.get("quality_score")
            score_str = f"{score:.2f}" if isinstance(score, float) else str(score)
            passed = "✓" if c.get("passed") else ("✗" if c.get("passed") is False else "?")
            reason = (c.get("judge_reason") or "")[:50]
            print(f"  {c['id']:<15} {c.get('expected_behavior','?'):<8} {score_str:<7} {passed:<6} {reason}")

    print()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Error: {path} does not exist")
        sys.exit(1)
    results_path = find_results(path)
    summarize(results_path)


if __name__ == "__main__":
    main()
