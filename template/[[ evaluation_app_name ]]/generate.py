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
Generate synthetic evaluation test cases using Claude.

Usage:
    python generate.py \
        --agent-description "A content planner and writer agent that researches topics and writes articles" \
        --n 10 \
        --output user_datasets/generated_cases.json

Review and edit the output before using it in evaluations.
"""

import argparse
from pathlib import Path

from evaluator.generator import CaseGenerator


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate synthetic evaluation test cases using Claude"
    )
    parser.add_argument(
        "--agent-description",
        required=True,
        help="Description of what the agent does, what it should and shouldn't do",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=10,
        help="Total number of cases to generate (split evenly good/bad, default: 10)",
    )
    parser.add_argument(
        "--n-good",
        type=int,
        help="Number of good cases (overrides --n split)",
    )
    parser.add_argument(
        "--n-bad",
        type=int,
        help="Number of bad cases (overrides --n split)",
    )
    parser.add_argument(
        "--output",
        default="user_datasets/generated_cases.json",
        help="Output file path (default: user_datasets/generated_cases.json)",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append to existing file instead of overwriting",
    )
    args = parser.parse_args()

    n_good = args.n_good if args.n_good is not None else args.n // 2
    n_bad = args.n_bad if args.n_bad is not None else args.n - n_good

    print(f"Generating {n_good} good + {n_bad} bad test cases...")

    generator = CaseGenerator()
    cases = generator.generate(args.agent_description, n_good, n_bad)
    written = generator.save(cases, Path(args.output), append=args.append)

    print(f"Wrote {len(written)} cases to {args.output}")
    print()
    print("Review and edit before using in evaluations:")
    for case in written:
        behavior_label = "✓" if case["expected_behavior"] == "good" else "✗"
        print(f"  [{behavior_label}] {case['id']}: {case['input'][:70]}")


if __name__ == "__main__":
    main()
