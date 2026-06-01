#!/usr/bin/env python3
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
