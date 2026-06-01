from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from evaluator.runner import run_byob


def _cfg() -> dict[str, Any]:
    return {
        "benchmark": {"module": "benchmarks/agent_quality_safety.py", "name": "agent_quality_safety"},
        "target": {"model_type": "chat", "model_id": "unknown"},
        "judge": {
            "url": "https://judge.example.com",
            "model_id": "gpt-4o",
            "api_key_name": "JUDGE_KEY",
        },
        "run": {"parallelism": 2, "max_tokens": 512, "temperature": 0.0, "timeout_per_sample": 60},
    }


def test_run_byob_invokes_subprocess(tmp_path: Path) -> None:
    mock_result = MagicMock()
    mock_result.returncode = 0

    with patch("evaluator.runner.subprocess.run", return_value=mock_result) as mock_run:
        run_byob(_cfg(), "http://agent/v1", "/tmp/dataset.jsonl", "/tmp/output", tmp_path)

    assert mock_run.called
    cmd = mock_run.call_args[0][0]
    assert "-m" in cmd
    assert "nemo_evaluator.contrib.byob.runner" in cmd


def test_run_byob_passes_required_flags(tmp_path: Path) -> None:
    mock_result = MagicMock()
    mock_result.returncode = 0

    with patch("evaluator.runner.subprocess.run", return_value=mock_result) as mock_run:
        run_byob(_cfg(), "http://agent/v1", "/tmp/ds.jsonl", "/tmp/out", tmp_path)

    cmd = mock_run.call_args[0][0]
    assert "--benchmark-module" in cmd
    assert "--benchmark-name" in cmd
    assert "--dataset" in cmd
    assert "--model-url" in cmd
    assert "--output-dir" in cmd
    assert "--save-predictions" in cmd


def test_run_byob_sets_judge_env_vars(tmp_path: Path) -> None:
    mock_result = MagicMock()
    mock_result.returncode = 0

    with patch("evaluator.runner.subprocess.run", return_value=mock_result) as mock_run:
        run_byob(_cfg(), "http://agent/v1", "/tmp/ds.jsonl", "/tmp/out", tmp_path)

    env = mock_run.call_args[1]["env"]
    assert env["JUDGE_URL"] == "https://judge.example.com"
    assert env["JUDGE_MODEL_ID"] == "gpt-4o"
    assert env["JUDGE_API_KEY_NAME"] == "JUDGE_KEY"


def test_run_byob_raises_on_nonzero_exit(tmp_path: Path) -> None:
    mock_result = MagicMock()
    mock_result.returncode = 1

    with patch("evaluator.runner.subprocess.run", return_value=mock_result):
        with pytest.raises(RuntimeError, match="BYOB runner exited"):
            run_byob(_cfg(), "http://agent/v1", "/tmp/ds.jsonl", "/tmp/out", tmp_path)


def test_run_byob_does_not_pass_api_key_flag_when_env_var_unset(tmp_path: Path) -> None:
    """api_key_name is only forwarded if the env var is actually set."""
    cfg = _cfg()
    cfg["target"]["api_key_name"] = "AGENT_API_KEY"
    mock_result = MagicMock()
    mock_result.returncode = 0

    with patch("evaluator.runner.subprocess.run", return_value=mock_result) as mock_run, \
         patch.dict("os.environ", {}, clear=True):
        run_byob(cfg, "http://agent/v1", "/tmp/ds.jsonl", "/tmp/out", tmp_path)

    cmd = mock_run.call_args[0][0]
    assert "--api-key-name" not in cmd
