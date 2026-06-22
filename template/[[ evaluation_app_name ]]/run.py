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
"""NeMo Evaluator batch evaluation CLI (BYOB / in-process — no Docker).

Thin wrapper around datarobot_genai.eval.cli.run_main. All logic lives in the
package; this file only pins the component directory (where user_pipelines/,
user_datasets/, and output/ live) so the external CLI can invoke `python run.py`.
"""

from pathlib import Path

from datarobot_genai.eval.cli import run_main


def main() -> None:
    run_main(repo_root=Path(__file__).parent)


if __name__ == "__main__":
    main()
