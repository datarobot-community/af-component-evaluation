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
"""Built-in NeMo BYOB benchmarks shipped with this evaluation component.

Each module here is a *self-contained* benchmark: one case type, one scoring
strategy, no cross-imports between benchmarks. That isolation is deliberate —
copy any single file to ``user_pipelines/`` as the starting point for a custom
benchmark without dragging in a chain of shared helpers.

Benchmarks split into two families, distinguished by whether their pipeline YAML
carries a ``judge:`` section:

    Judge-based (LLM-as-judge):  answer_quality, safety_refusal, faithfulness
    Judge-free (deterministic):  answer_correctness, instruction_following,
                                 prompt_injection, pii_leakage, tool_grounding

The runner loads a benchmark by file path (``--benchmark-module``); these are
importable as a package only so the deterministic scorers can be unit-tested.
"""
