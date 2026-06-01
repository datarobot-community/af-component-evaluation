from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError

import pytest
import yaml

from evaluator.validation import health_check, load_pipeline, validate_inputs

# ---------------------------------------------------------------------------
# health_check
# ---------------------------------------------------------------------------


def test_health_check_returns_none_on_success() -> None:
    with patch("evaluator.validation.urlopen"):
        assert health_check("http://localhost:8842/v1") is None


def test_health_check_returns_none_on_http_error() -> None:
    # Any HTTP response (even 4xx) means the server is up
    with patch(
        "evaluator.validation.urlopen",
        side_effect=HTTPError(None, 404, "Not Found", {}, None),
    ):  # type: ignore[arg-type]
        assert health_check("http://localhost:8842/v1") is None


def test_health_check_returns_error_on_url_error() -> None:
    with patch(
        "evaluator.validation.urlopen", side_effect=URLError("connection refused")
    ):
        result = health_check("http://localhost:8842/v1")
    assert result is not None
    assert "not reachable" in result


def test_health_check_returns_error_on_unexpected_exception() -> None:
    with patch("evaluator.validation.urlopen", side_effect=OSError("timeout")):
        result = health_check("http://localhost:8842/v1")
    assert result is not None


# ---------------------------------------------------------------------------
# load_pipeline
# ---------------------------------------------------------------------------


def test_load_pipeline_valid(pipeline_yaml_path: Path) -> None:
    cfg = load_pipeline(pipeline_yaml_path)
    assert "benchmark" in cfg
    assert "target" in cfg
    assert "judge" in cfg


def test_load_pipeline_missing_section(tmp_path: Path) -> None:
    incomplete = {"benchmark": {"module": "b.py", "name": "b"}, "target": {}}
    p = tmp_path / "incomplete.yaml"
    p.write_text(yaml.dump(incomplete))
    with pytest.raises(ValueError, match="missing required section"):
        load_pipeline(p)


def test_load_pipeline_not_mapping(tmp_path: Path) -> None:
    p = tmp_path / "bad.yaml"
    p.write_text("- item1\n- item2\n")
    with pytest.raises(ValueError, match="did not parse to a mapping"):
        load_pipeline(p)


# ---------------------------------------------------------------------------
# validate_inputs
# ---------------------------------------------------------------------------


def test_validate_inputs_all_pass(
    tmp_path: Path, pipeline_yaml_path: Path, dataset_path: Path
) -> None:
    pipelines_dir = pipeline_yaml_path.parent
    with patch("evaluator.validation.health_check", return_value=None):
        errors = validate_inputs(
            "http://localhost/v1",
            "test_pipeline.yaml",
            str(dataset_path),
            pipelines_dir,
            tmp_path,
        )
    assert errors == []


def test_validate_inputs_endpoint_unreachable(
    tmp_path: Path, pipeline_yaml_path: Path, dataset_path: Path
) -> None:
    pipelines_dir = pipeline_yaml_path.parent
    with patch("evaluator.validation.health_check", return_value="not reachable"):
        errors = validate_inputs(
            "http://bad",
            "test_pipeline.yaml",
            str(dataset_path),
            pipelines_dir,
            tmp_path,
        )
    assert any("Health check failed" in e for e in errors)


def test_validate_inputs_missing_pipeline(tmp_path: Path, dataset_path: Path) -> None:
    pipelines_dir = tmp_path / "pipelines"
    pipelines_dir.mkdir()
    with patch("evaluator.validation.health_check", return_value=None):
        errors = validate_inputs(
            "http://localhost/v1",
            "nonexistent.yaml",
            str(dataset_path),
            pipelines_dir,
            tmp_path,
        )
    assert any("not found" in e for e in errors)


def test_validate_inputs_missing_dataset(
    tmp_path: Path, pipeline_yaml_path: Path
) -> None:
    pipelines_dir = pipeline_yaml_path.parent
    with patch("evaluator.validation.health_check", return_value=None):
        errors = validate_inputs(
            "http://localhost/v1",
            "test_pipeline.yaml",
            str(tmp_path / "missing.json"),
            pipelines_dir,
            tmp_path,
        )
    assert any("Dataset not found" in e for e in errors)


def test_validate_inputs_missing_benchmark_module(
    tmp_path: Path, dataset_path: Path
) -> None:
    # Pipeline references a benchmark module that doesn't exist
    import yaml as _yaml

    pipelines_dir = tmp_path / "pipelines"
    pipelines_dir.mkdir()
    cfg = {
        "benchmark": {"module": "benchmarks/missing.py", "name": "x"},
        "target": {},
        "judge": {},
    }
    (pipelines_dir / "p.yaml").write_text(_yaml.dump(cfg))

    with patch("evaluator.validation.health_check", return_value=None):
        errors = validate_inputs(
            "http://localhost/v1",
            "p.yaml",
            str(dataset_path),
            pipelines_dir,
            tmp_path,
        )
    assert any("Benchmark module not found" in e for e in errors)


def test_validate_inputs_collects_multiple_errors(tmp_path: Path) -> None:
    pipelines_dir = tmp_path / "pipelines"
    pipelines_dir.mkdir()
    with patch("evaluator.validation.health_check", return_value="bad endpoint"):
        errors = validate_inputs(
            "http://bad",
            "missing.yaml",
            str(tmp_path / "missing.json"),
            pipelines_dir,
            tmp_path,
        )
    assert len(errors) >= 2
