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
"""Integration smoke tests for all three CLI commands.

Two tests require live DR credentials and are skipped when absent:
    DATAROBOT_API_TOKEN  bearer token for the DR LLM gateway
    DATAROBOT_ENDPOINT   base API URL, e.g. https://app.datarobot.com/api/v2

The agent under test is a lightweight in-process mock that returns a canned
OpenAI-compatible response (see conftest.mock_agent_endpoint). Only judge and
generator calls are live.

Run locally (after setting the env vars or sourcing .env):
    uv run python -m pytest -m integration -vv
"""

import json
import os
from pathlib import Path
from typing import Any

import pytest
import yaml
from datarobot_genai.eval.cli import generate_main, run_main, summarize_main

_RESULTS: dict[str, Any] = {
    "run_id": "20260601_120000",
    "completed_at": "2026-06-01T12:00:00+00:00",
    "agent_endpoint": "http://localhost/v1",
    "pipeline": "smoke.yaml",
    "total_cases": 1,
    "summary": {
        "scored_cases": 1,
        "inconclusive_cases": 0,
        "mean_score": 1.0,
        "pass_rate": 1.0,
        "good_case_pass_rate": 1.0,
        "bad_case_pass_rate": None,
    },
    "cases": [
        {
            "id": "smoke-001",
            "input": "What is 2+2?",
            "expected_behavior": "good",
            "agent_response": "The answer is 4.",
            "score": 1.0,
            "passed": True,
            "reason": "judge grade: 5",
        }
    ],
}

_NEEDS_CREDS = pytest.mark.skipif(
    not os.environ.get("DATAROBOT_API_TOKEN")
    or not os.environ.get("DATAROBOT_ENDPOINT"),
    reason="DATAROBOT_API_TOKEN and DATAROBOT_ENDPOINT must be set",
)


@pytest.mark.integration
@_NEEDS_CREDS
def test_answer_quality_smoke(tmp_path: Path, mock_agent_endpoint: str) -> None:
    """Run one good case through the full answer_quality pipeline end-to-end.

    Validates: agent call → DR judge → NeMo metric → result normalisation.
    A passing grade from the judge confirms credentials, gateway reachability,
    and the full datarobot_genai.eval pipeline in a single fast shot.
    """
    dr_endpoint = os.environ["DATAROBOT_ENDPOINT"].rstrip("/")
    judge_url = f"{dr_endpoint}/genai/llmgw"

    pipeline_cfg = {
        "benchmark": {
            "module": "datarobot_genai/eval/benchmarks/answer_quality.py",
            "name": "answer_quality",
        },
        "target": {"model_type": "chat", "model_id": "unknown"},
        "judge": {
            "url": judge_url,
            "model_id": "bedrock/anthropic.claude-haiku-4-5-20251001-v1:0",
            "api_key_name": "DATAROBOT_API_TOKEN",
        },
        "run": {
            "parallelism": 1,
            "max_tokens": 256,
            "temperature": 0.0,
            "timeout_per_sample": 60,
        },
    }

    pipelines_dir = tmp_path / "user_pipelines"
    pipelines_dir.mkdir()
    (pipelines_dir / "smoke.yaml").write_text(yaml.dump(pipeline_cfg))

    dataset = [
        {
            "id": "smoke-001",
            "input": "What is 2+2?",
            "expected_behavior": "good",
            "source": "collected",
        }
    ]
    dataset_path = tmp_path / "cases.json"
    dataset_path.write_text(json.dumps(dataset))

    with pytest.raises(SystemExit) as exc:
        run_main(
            argv=[
                "--endpoint",
                mock_agent_endpoint,
                "--pipeline",
                "smoke.yaml",
                "--dataset",
                str(dataset_path),
            ],
            repo_root=tmp_path,
        )

    assert exc.value.code == 0, (
        "run_main exited non-zero — check output above for details"
    )

    results_path = tmp_path / "output" / "eval_results.json"
    assert results_path.exists(), "eval_results.json was not written"

    results = json.loads(results_path.read_text())
    summary = results["summary"]
    assert results["total_cases"] == 1
    assert summary["inconclusive_cases"] == 0, (
        f"Judge returned inconclusive — possible gateway error or bad credentials. "
        f"summary={summary}"
    )
    assert summary["scored_cases"] == 1
    # 1 unambiguous good case ("What is 2+2?" → "The answer is 4.") must pass.
    # A score below 1.0 indicates a judge problem, not genuine eval variance.
    assert summary["pass_rate"] == 1.0, (
        f"Expected pass_rate=1.0 for a trivially correct response, "
        f"got {summary['pass_rate']}. cases={results['cases']}"
    )


@pytest.mark.integration
def test_summarize_smoke(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Summarize a results file — exercises the full display codepath.

    No credentials needed; included here so the smoke job exercises all three
    CLI commands in a single run.
    """
    results_path = tmp_path / "eval_results.json"
    results_path.write_text(json.dumps(_RESULTS))

    summarize_main(argv=[str(results_path)])

    out = capsys.readouterr().out
    # Case ID and a passing checkmark must appear in the per-case table.
    assert "smoke-001" in out
    assert "✓" in out, f"Expected a passing checkmark in summarize output, got:\n{out}"
    # Per-case score column renders floats to 2 decimal places.
    assert "1.00" in out, f"Expected score 1.00 in per-case table, got:\n{out}"


@pytest.mark.integration
@_NEEDS_CREDS
def test_generate_smoke(tmp_path: Path) -> None:
    """Generate one synthetic test case via the DR LLM gateway.

    Validates: CaseGenerator → litellm → DR gateway → JSON output.
    Uses --n-good 1 --n-bad 0 to keep the call fast and cheap.
    """
    output_path = tmp_path / "generated.json"

    generate_main(
        argv=[
            "--agent-description",
            "A simple Q&A assistant that answers factual questions.",
            "--n-good",
            "1",
            "--n-bad",
            "0",
            "--model-id",
            "datarobot/bedrock/anthropic.claude-sonnet-4-6",
            "--output",
            str(output_path),
        ],
        repo_root=tmp_path,
    )

    assert output_path.exists(), "generated cases file was not written"
    cases = json.loads(output_path.read_text())
    assert len(cases) >= 1, f"Expected at least 1 generated case, got {len(cases)}"
    # All cases should be good — we asked for 0 bad cases.
    assert all(c["expected_behavior"] == "good" for c in cases)
    assert all(c.get("input") for c in cases)
