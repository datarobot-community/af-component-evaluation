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
Generate or convert evaluation test cases.

Generate synthetic cases using a DataRobot-hosted model:
    python generate.py \
        --agent-description "A content planner and writer agent that researches topics and writes articles" \
        --n 10 \
        --output user_datasets/generated_cases.json

Convert an existing CSV to JSON:
    python generate.py \
        --convert user_datasets/my_cases.csv \
        --output user_datasets/my_cases.json

Review and edit the output before using it in evaluations.
"""

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml
from evaluator.converter import convert_csv_to_cases, save_cases

from evaluator.generator import CaseGenerator
from evaluator.validation import preflight_judge


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate synthetic evaluation test cases or convert a CSV dataset to JSON"
    )

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--agent-description",
        help="Description of what the agent does (triggers synthetic generation via a DataRobot-hosted model)",
    )
    mode.add_argument(
        "--convert",
        metavar="CSV_FILE",
        help="Path to a CSV file to convert to JSON (columns: id, source, input required; others optional)",
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
        help=(
            "Output JSON file path. "
            "Defaults to user_datasets/generated_cases.json for generation, "
            "or <csv_stem>.json in the same directory for --convert."
        ),
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append to existing file instead of overwriting (generation only)",
    )
    parser.add_argument(
        "--pipeline",
        metavar="YAML_FILE",
        help=(
            "Pipeline YAML (e.g. user_pipelines/answer_quality.yaml). "
            "When provided, the generator tailors good/bad criteria and required "
            "fields to match the benchmark."
        ),
    )
    args = parser.parse_args()

    if args.convert:
        csv_path = Path(args.convert)
        if not csv_path.exists():
            parser.error(f"CSV file not found: {csv_path}")

        output_path = (
            Path(args.output) if args.output else csv_path.with_suffix(".json")
        )

        print(f"Converting {csv_path} -> {output_path} ...")
        cases = convert_csv_to_cases(csv_path)
        save_cases(cases, output_path)
        print(f"Wrote {len(cases)} cases to {output_path}")
        print()
        print("Review and edit before using in evaluations:")
        for case in cases:
            print(f"  {case['id']}: {str(case['input'])[:70]}")
        return

    # --- generation mode ---
    n_good = args.n_good if args.n_good is not None else args.n // 2
    n_bad = args.n_bad if args.n_bad is not None else args.n - n_good
    output_path = (
        Path(args.output) if args.output else Path("user_datasets/generated_cases.json")
    )

    benchmark_name: str | None = None
    if args.pipeline:
        pipeline_path = Path(args.pipeline)
        if not pipeline_path.exists():
            parser.error(f"Pipeline file not found: {pipeline_path}")
        pipeline_cfg: dict[str, Any] = yaml.safe_load(pipeline_path.read_text())
        benchmark_name = (pipeline_cfg.get("benchmark") or {}).get("name")
        if benchmark_name:
            print(f"Tailoring cases for benchmark: {benchmark_name}")
        judge_cfg = pipeline_cfg.get("judge")
        if judge_cfg:
            try:
                preflight_judge(judge_cfg)
            except RuntimeError as e:
                print(f"ERROR: {e}", file=sys.stderr)
                raise SystemExit(1) from e
            print(f"Judge reachable: {judge_cfg['model_id']}")

    print(f"Generating {n_good} good + {n_bad} bad test cases...")

    generator = CaseGenerator()
    cases = generator.generate(
        args.agent_description, n_good, n_bad, benchmark_name=benchmark_name
    )
    written = generator.save(cases, output_path, append=args.append)

    print(f"Wrote {len(written)} cases to {output_path}")
    print()
    print("Review and edit before using in evaluations:")
    for case in written:
        behavior_label = "✓" if case["expected_behavior"] == "good" else "✗"
        print(f"  [{behavior_label}] {case['id']}: {case['input'][:70]}")


if __name__ == "__main__":
    main()
