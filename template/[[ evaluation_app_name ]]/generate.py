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
"""Generate or convert evaluation test cases.

Thin wrapper around datarobot_genai.eval.cli.generate_main.

Generate synthetic cases using a DataRobot-hosted model:
    python generate.py \
        --agent-description "A content planner and writer agent that researches topics" \
        --n 10 \
        --output user_datasets/generated_cases.json

Convert an existing CSV to JSON:
    python generate.py --convert user_datasets/my_cases.csv --output user_datasets/my_cases.json

Review and edit the output before using it in evaluations.
"""

from pathlib import Path

from datarobot_genai.eval.cli import generate_main


def main() -> None:
    generate_main(repo_root=Path(__file__).parent)


if __name__ == "__main__":
    main()
