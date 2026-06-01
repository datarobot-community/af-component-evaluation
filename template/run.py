#!/usr/bin/env python3
"""
NeMo Evaluator batch evaluation CLI (BYOB / in-process — no Docker).

The external CLI passes three things:
  --endpoint   Base URL of the agent's OpenAI-compatible API
  --pipeline   Filename of a pipeline YAML in pipelines/
  --dataset    Path to a test case JSON file (defaults to user_datasets/sample_cases.json)

Fixed output locations (always the same — external CLI can rely on these paths):
  output/eval_status.json     current run status
  output/eval_results.json    normalized results (written on success)

Exit codes:
  0  success
  1  validation error (bad endpoint, missing pipeline/dataset)
  2  evaluator subprocess failed
  3  output normalization failed
"""

import argparse
import sys
from pathlib import Path

from evaluator.eval import EvalRunner

_REPO_ROOT = Path(__file__).parent
_DEFAULT_DATASET = str(_REPO_ROOT / "user_datasets" / "sample_cases.json")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run NeMo Evaluator batch evaluation (BYOB, in-process)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--endpoint",
        required=True,
        help="Base URL of the agent's OpenAI-compatible API (e.g. http://localhost:8842/v1)",
    )
    parser.add_argument(
        "--pipeline",
        required=True,
        help="Pipeline YAML filename in pipelines/ (e.g. agent_quality_safety.yaml)",
    )
    parser.add_argument(
        "--dataset",
        default=_DEFAULT_DATASET,
        help=f"Path to test case JSON file (default: {_DEFAULT_DATASET})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs and print what would run, without executing",
    )
    args = parser.parse_args()

    runner = EvalRunner(
        endpoint=args.endpoint,
        pipeline=args.pipeline,
        dataset=args.dataset,
    )
    sys.exit(runner.run(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
