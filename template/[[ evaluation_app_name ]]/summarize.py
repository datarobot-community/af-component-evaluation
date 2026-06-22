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
"""Pretty-print a normalized eval_results.json from a completed run.

Thin wrapper around datarobot_genai.eval.cli.summarize_main.

Usage:
    python summarize.py output/
    python summarize.py output/eval_results.json
"""

from datarobot_genai.eval.cli import summarize_main


def main() -> None:
    summarize_main()


if __name__ == "__main__":
    main()
