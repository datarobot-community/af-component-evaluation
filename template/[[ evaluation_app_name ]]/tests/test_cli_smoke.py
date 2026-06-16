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
Smoke tests for the CLI entrypoints (generate.py, run.py, summarize.py).

These guard against the most common breakage: a datarobot-genai upgrade
removes or renames a `datarobot_genai.eval.*` symbol that an entrypoint
imports at module load, silently breaking the CLI. They run entirely
in-process with no LLM, no network, and no DataRobot credentials — just
enough to prove each entrypoint imports, builds its argument parser, and
runs its no-model codepaths.
"""

import importlib
import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

_ENTRYPOINTS = ["generate", "run", "summarize"]

_PIPELINE_CFG: dict[str, Any] = {
    "benchmark": {
        "module": "datarobot_genai/eval/benchmarks/answer_quality.py",
        "name": "answer_quality",
    },
    "target": {"model_type": "chat", "model_id": "unknown"},
    "judge": None,
    "run": {},
}

_RESULTS: dict[str, Any] = {
    "run_id": "20260601_120000",
    "completed_at": "2026-06-01T12:00:00+00:00",
    "agent_endpoint": "http://localhost/v1",
    "pipeline": "answer_quality.yaml",
    "total_cases": 1,
    "summary": {
        "scored_cases": 1,
        "inconclusive_cases": 0,
        "mean_quality_score": 1.0,
        "pass_rate": 1.0,
        "good_case_pass_rate": 1.0,
        "bad_case_pass_rate": None,
        "nemo_aggregate": {},
    },
    "cases": [
        {
            "id": "c-001",
            "input": "hello",
            "expected_behavior": "good",
            "agent_response": "hi",
        }
    ],
}


# ---------------------------------------------------------------------------
# Import smoke — catches removed/renamed datarobot_genai.eval.* symbols
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module_name", _ENTRYPOINTS)
def test_entrypoint_imports(module_name: str) -> None:
    """Importing executes the top-level `from datarobot_genai.eval...` lines."""
    assert importlib.import_module(module_name) is not None


# ---------------------------------------------------------------------------
# --help builds the argument parser (argparse CLIs) and exits 0
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("module_name", ["generate", "run"])
def test_help_exits_zero(module_name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    module = importlib.import_module(module_name)
    monkeypatch.setattr(sys, "argv", [f"{module_name}.py", "--help"])
    with pytest.raises(SystemExit) as exc:
        module.main()
    assert exc.value.code == 0


# ---------------------------------------------------------------------------
# generate --convert: real CSV -> JSON, no model involved
# ---------------------------------------------------------------------------


def test_generate_convert(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    generate = importlib.import_module("generate")
    csv_path = tmp_path / "cases.csv"
    csv_path.write_text(
        "id,source,input,notes\n"
        "c-001,collected,What is 2+2?,arithmetic\n"
        "c-002,collected,Capital of France?,geography\n"
    )
    out_path = tmp_path / "cases.json"
    monkeypatch.setattr(
        sys,
        "argv",
        ["generate.py", "--convert", str(csv_path), "--output", str(out_path)],
    )

    generate.main()

    cases = json.loads(out_path.read_text())
    assert [c["id"] for c in cases] == ["c-001", "c-002"]


# ---------------------------------------------------------------------------
# summarize: pretty-print a results file — the eval display codepath
# ---------------------------------------------------------------------------


def test_summarize_prints_results(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    summarize = importlib.import_module("summarize")
    results_path = tmp_path / "eval_results.json"
    results_path.write_text(json.dumps(_RESULTS))
    monkeypatch.setattr(sys, "argv", ["summarize.py", str(results_path)])

    summarize.main()  # must not raise

    assert capsys.readouterr().out.strip()  # produced some summary output


# ---------------------------------------------------------------------------
# run --dry-run: exercises run.py's main() wiring without a network call
# ---------------------------------------------------------------------------


def test_run_dry_run_exits_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    run = importlib.import_module("run")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run.py",
            "--endpoint",
            "http://localhost/v1",
            "--pipeline",
            "answer_quality.yaml",
            "--dry-run",
        ],
    )
    with (
        patch("datarobot_genai.eval.eval.validate_inputs", return_value=[]),
        patch("datarobot_genai.eval.eval.load_pipeline", return_value=_PIPELINE_CFG),
        pytest.raises(SystemExit) as exc,
    ):
        run.main()
    assert exc.value.code == 0
