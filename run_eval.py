#!/usr/bin/env python3
"""
NeMo Evaluator batch evaluation CLI (BYOB / in-process — no Docker).

The external CLI passes three things:
  --endpoint   Base URL of the agent's OpenAI-compatible API
  --pipeline   Filename of a pipeline YAML in pipelines/
  --dataset    Path to a test case JSON file (defaults to datasets/sample_cases.json)

This script:
  1. Validates that the endpoint is reachable, pipeline exists, dataset exists
  2. Writes output/eval_status.json  →  {"status": "running", ...}
  3. Converts dataset to the BYOB JSONL format
  4. Reads the pipeline YAML (benchmark module + judge config + run params)
  5. Runs the NeMo BYOB runner in-process as a subprocess
  6. Normalizes raw output into output/eval_results.json  (schema: schemas/output_schema.json)
  7. Updates output/eval_status.json  →  {"status": "complete"} or {"status": "failed"}

Why BYOB (and not nemo-evaluator-launcher):
  The launcher runs every task in an nvcr.io Docker container (--gpus all) and
  exposes only fixed benchmarks (MMLU, GSM8K, MTBench, ...). There is no generic
  "custom Q&A + LLM judge" task, and the Docker path won't run on a laptop. NeMo's
  BYOB framework (nemo_evaluator.contrib.byob) runs a custom benchmark in-process,
  which is exactly what we need. See BUGS.md for the LiteLLM / Bedrock notes.

Fixed output locations (always the same — external CLI can rely on these paths):
  output/eval_status.json     current run status
  output/eval_results.json    normalized results (written on success)

Exit codes:
  0  success
  1  validation error (bad endpoint, missing pipeline/dataset)
  2  evaluator subprocess failed
  3  output normalization failed
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import yaml

REPO_ROOT = Path(__file__).parent
PIPELINES_DIR = REPO_ROOT / "pipelines"
DATASETS_DIR = REPO_ROOT / "datasets"
OUTPUT_DIR = REPO_ROOT / "output"
DEFAULT_DATASET = DATASETS_DIR / "sample_cases.json"

PASS_THRESHOLD = 0.5


# ---------------------------------------------------------------------------
# Status file — external CLI polls this
# ---------------------------------------------------------------------------


def write_status(
    status: str,
    run_id: str,
    pipeline: str,
    endpoint: str,
    error: str | None = None,
) -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)
    payload = {
        "status": status,  # running | complete | failed
        "run_id": run_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "pipeline": pipeline,
        "agent_endpoint": endpoint,
        "error": error,
    }
    (OUTPUT_DIR / "eval_status.json").write_text(json.dumps(payload, indent=2))


# ---------------------------------------------------------------------------
# Pre-flight validation
# ---------------------------------------------------------------------------


def health_check(endpoint_url: str) -> str | None:
    """Return None if the server responds at all, else an error string.

    A DRUM agentic-workflow server exposes /chat/completions but not
    necessarily /v1/models, so any HTTP response (even 4xx/405) means the
    server is up and reachable. Only a connection-level failure is fatal.
    """
    base = endpoint_url.rstrip("/")
    try:
        req = Request(base, headers={"Accept": "application/json"})
        urlopen(req, timeout=10)
        return None
    except HTTPError:
        # Server responded (e.g. 404/405 on the root path) — it's reachable.
        return None
    except URLError as e:
        return f"Endpoint not reachable at {base}: {e.reason}"
    except Exception as e:  # noqa: BLE001
        return f"Endpoint check failed: {e}"


def load_pipeline(pipeline_path: Path) -> dict:
    cfg = yaml.safe_load(pipeline_path.read_text())
    if not isinstance(cfg, dict):
        raise ValueError(f"Pipeline {pipeline_path} did not parse to a mapping")
    for key in ("benchmark", "target", "judge"):
        if key not in cfg:
            raise ValueError(f"Pipeline {pipeline_path} missing required section: {key}")
    return cfg


def validate_inputs(endpoint: str, pipeline: str, dataset: str) -> list[str]:
    errors = []

    error = health_check(endpoint)
    if error:
        errors.append(f"Health check failed — {error}")

    pipeline_path = PIPELINES_DIR / pipeline
    if not pipeline_path.exists():
        available = [f.name for f in PIPELINES_DIR.glob("*.yaml")]
        errors.append(
            f"Pipeline '{pipeline}' not found in pipelines/. Available: {available or 'none'}"
        )
    else:
        try:
            cfg = load_pipeline(pipeline_path)
            module = REPO_ROOT / cfg["benchmark"]["module"]
            if not module.exists():
                errors.append(f"Benchmark module not found: {module}")
        except (ValueError, KeyError) as e:
            errors.append(f"Pipeline '{pipeline}' invalid: {e}")

    if not Path(dataset).exists():
        errors.append(f"Dataset not found: {dataset}")

    return errors


# ---------------------------------------------------------------------------
# Dataset conversion: our schema → BYOB JSONL
# Each row carries the prompt field + all metadata fields. The benchmark's
# scorer reads expected_behavior/notes from the row (row → ScorerInput.metadata).
# ---------------------------------------------------------------------------


def load_dataset(path: str) -> list[dict]:
    text = Path(path).read_text()
    if path.endswith(".jsonl"):
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    return json.loads(text)


def to_byob_jsonl(dataset: list[dict], output_path: str) -> None:
    lines = []
    for case in dataset:
        row = {
            "id": case["id"],
            "input": case["input"],
            "ideal_response": case.get("ideal_response"),
            "expected_behavior": case.get("expected_behavior", "good"),
            "notes": case.get("notes", ""),
            "source": case.get("source", ""),
        }
        lines.append(json.dumps(row))
    Path(output_path).write_text("\n".join(lines))


# ---------------------------------------------------------------------------
# Run the BYOB runner (in-process NeMo Evaluator — same venv as this script)
# ---------------------------------------------------------------------------


def run_byob(
    cfg: dict,
    endpoint: str,
    dataset_jsonl: str,
    output_dir: str,
) -> None:
    benchmark = cfg["benchmark"]
    target = cfg["target"]
    judge = cfg["judge"]
    run = cfg.get("run", {})

    module_path = str((REPO_ROOT / benchmark["module"]).absolute())

    env = {
        **os.environ,
        # Judge config consumed by benchmarks/*.py at import time.
        "JUDGE_URL": str(judge["url"]),
        "JUDGE_MODEL_ID": str(judge["model_id"]),
        "JUDGE_API_KEY_NAME": str(judge.get("api_key_name", "DATAROBOT_API_TOKEN")),
    }

    cmd = [
        sys.executable,
        "-m",
        "nemo_evaluator.contrib.byob.runner",
        "--benchmark-module", module_path,
        "--benchmark-name", str(benchmark["name"]),
        "--dataset", dataset_jsonl,
        "--model-type", str(target.get("model_type", "chat")),
        "--model-url", endpoint,
        "--model-id", str(target.get("model_id", "datarobot-agent")),
        "--output-dir", output_dir,
        "--save-predictions",
        "--parallelism", str(run.get("parallelism", 4)),
        "--max-tokens", str(run.get("max_tokens", 1024)),
        "--temperature", str(run.get("temperature", 0.0)),
        "--timeout-per-sample", str(run.get("timeout_per_sample", 180)),
    ]

    # Only pass the target API key name if that env var is actually set. A local
    # DRUM agent needs no auth; the runner errors if the name is given but unset.
    target_key_name = target.get("api_key_name")
    if target_key_name and os.environ.get(target_key_name):
        cmd += ["--api-key-name", str(target_key_name)]

    result = subprocess.run(cmd, env=env, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"BYOB runner exited with code {result.returncode}")


# ---------------------------------------------------------------------------
# Normalize BYOB output → our output schema
#   <output_dir>/<normalized_name>/byob_results.json       aggregate scores
#   <output_dir>/<normalized_name>/byob_predictions.jsonl  per-sample
# ---------------------------------------------------------------------------


def _find_artifact(output_dir: str, filename: str) -> Path | None:
    matches = sorted(Path(output_dir).rglob(filename))
    return matches[0] if matches else None


def normalize_output(
    output_dir: str,
    dataset: list[dict],
    endpoint: str,
    pipeline: str,
    run_id: str,
) -> dict:
    dataset_by_id = {c["id"]: c for c in dataset}

    predictions_path = _find_artifact(output_dir, "byob_predictions.jsonl")
    results_path = _find_artifact(output_dir, "byob_results.json")

    cases = []
    if predictions_path and predictions_path.exists():
        for line in predictions_path.read_text().splitlines():
            if not line.strip():
                continue
            pred = json.loads(line)
            meta = pred.get("metadata", {})
            case_id = meta.get("id", "unknown")
            original = dataset_by_id.get(case_id, {})

            scores = pred.get("scores") or {}
            quality_score = scores.get("score")
            grade = scores.get("judge_grade", "")
            status = pred.get("status", "")

            passed = (
                quality_score >= PASS_THRESHOLD
                if isinstance(quality_score, (int, float))
                else None
            )

            cases.append(
                {
                    "id": case_id,
                    "input": original.get("input", meta.get("input", "")),
                    "expected_behavior": meta.get(
                        "expected_behavior", original.get("expected_behavior")
                    ),
                    "agent_response": pred.get("response") or "",
                    "quality_score": quality_score,
                    "judge_reason": (
                        f"judge grade: {grade}"
                        if status == "scored"
                        else f"status: {status}"
                    ),
                    "passed": passed,
                    "answer_match_score": None,
                    "notes": original.get("notes", meta.get("notes", "")),
                    "source": original.get("source", meta.get("source", "")),
                }
            )

    # Aggregate scores straight from the BYOB results.json.
    nemo_aggregate = {}
    if results_path and results_path.exists():
        raw = json.loads(results_path.read_text())
        for task_name, task_data in raw.get("tasks", {}).items():
            for metric_name, metric_data in task_data.get("metrics", {}).items():
                for score_name, score_data in metric_data.get("scores", {}).items():
                    nemo_aggregate[f"{task_name}.{metric_name}.{score_name}"] = (
                        score_data.get("value")
                    )

    scored = [c for c in cases if isinstance(c["quality_score"], (int, float))]
    mean_score = sum(c["quality_score"] for c in scored) / len(scored) if scored else None
    pass_rate = sum(1 for c in scored if c["passed"]) / len(scored) if scored else None
    good = [c for c in scored if c["expected_behavior"] == "good"]
    bad = [c for c in scored if c["expected_behavior"] == "bad"]

    return {
        "run_id": run_id,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "agent_endpoint": endpoint,
        "pipeline": pipeline,
        "total_cases": len(dataset),
        "summary": {
            "mean_quality_score": round(mean_score, 4) if mean_score is not None else None,
            "pass_rate": round(pass_rate, 4) if pass_rate is not None else None,
            "good_case_pass_rate": (
                round(sum(1 for c in good if c["passed"]) / len(good), 4) if good else None
            ),
            "bad_case_pass_rate": (
                round(sum(1 for c in bad if c["passed"]) / len(bad), 4) if bad else None
            ),
            "nemo_aggregate": nemo_aggregate,
        },
        "cases": cases,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run NeMo Evaluator batch evaluation (BYOB, in-process)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--endpoint",
        required=True,
        help="Base URL of the agent's OpenAI-compatible API (e.g. http://localhost:8842/v1)",
    )
    parser.add_argument(
        "--pipeline",
        required=True,
        help="Pipeline YAML filename in pipelines/ (e.g. agent_quality_safety.yaml)",
    )
    parser.add_argument(
        "--dataset",
        default=str(DEFAULT_DATASET),
        help=f"Path to test case JSON file (default: {DEFAULT_DATASET})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs and print what would run, without executing",
    )
    args = parser.parse_args()

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    # --- 1. Validate ---
    print("Validating inputs...")
    errors = validate_inputs(args.endpoint, args.pipeline, args.dataset)
    if errors:
        print("Validation failed:", file=sys.stderr)
        for e in errors:
            print(f"  ✗ {e}", file=sys.stderr)
        sys.exit(1)
    print(f"  ✓ Endpoint reachable: {args.endpoint}")
    print(f"  ✓ Pipeline found:     pipelines/{args.pipeline}")
    print(f"  ✓ Dataset found:      {args.dataset}")

    pipeline_path = PIPELINES_DIR / args.pipeline
    cfg = load_pipeline(pipeline_path)

    if args.dry_run:
        print("\nDry run — all inputs valid. Would run BYOB benchmark:")
        print(f"  module:  {cfg['benchmark']['module']}")
        print(f"  judge:   {cfg['judge']['model_id']} @ {cfg['judge']['url']}")
        print(f"  output → output/eval_results.json")
        sys.exit(0)

    # --- 2. Mark as running ---
    write_status("running", run_id, args.pipeline, args.endpoint)
    print("\nStatus: running  (output/eval_status.json)")

    dataset = load_dataset(args.dataset)
    print(f"Loaded {len(dataset)} test cases")

    # --- 3. Convert dataset ---
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False, prefix="byob_dataset_"
    ) as f:
        dataset_jsonl = f.name
    to_byob_jsonl(dataset, dataset_jsonl)

    nemo_output_dir = str(OUTPUT_DIR / "raw" / run_id)

    # --- 4. Run BYOB ---
    print("Running NeMo Evaluator (BYOB, in-process)...")
    try:
        run_byob(cfg, args.endpoint, dataset_jsonl, nemo_output_dir)
    except RuntimeError as e:
        write_status("failed", run_id, args.pipeline, args.endpoint, error=str(e))
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(2)
    finally:
        if Path(dataset_jsonl).exists():
            os.unlink(dataset_jsonl)

    # --- 5. Normalize output ---
    try:
        normalized = normalize_output(
            nemo_output_dir, dataset, args.endpoint, args.pipeline, run_id
        )
    except Exception as e:  # noqa: BLE001
        write_status(
            "failed",
            run_id,
            args.pipeline,
            args.endpoint,
            error=f"Output normalization failed: {e}",
        )
        print(f"ERROR normalizing output: {e}", file=sys.stderr)
        sys.exit(3)

    # --- 6. Write to fixed output location ---
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "eval_results.json").write_text(json.dumps(normalized, indent=2))
    write_status("complete", run_id, args.pipeline, args.endpoint)

    s = normalized["summary"]
    print("\nStatus: complete")
    print("Results: output/eval_results.json")
    print(f"  Total cases:        {normalized['total_cases']}")
    print(f"  Mean quality score: {s['mean_quality_score']}")
    print(f"  Pass rate:          {s['pass_rate']}")
    print(f"  Good case pass:     {s['good_case_pass_rate']}")
    print(f"  Bad case pass:      {s['bad_case_pass_rate']}")


if __name__ == "__main__":
    main()
