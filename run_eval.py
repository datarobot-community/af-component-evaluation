#!/usr/bin/env python3
"""
NeMo Evaluator batch evaluation CLI.

The external CLI passes three things:
  --endpoint   Base URL of the agent's OpenAI-compatible API
  --pipeline   Filename of a NeMo pipeline YAML in pipelines/
  --dataset    Path to a test case JSON file (defaults to datasets/sample_cases.json)

This script:
  1. Validates that the endpoint is reachable, pipeline exists, dataset exists
  2. Writes output/eval_status.json  →  {"status": "running", ...}
  3. Converts dataset to NeMo's JSONL format
  4. Renders the pipeline YAML with runtime substitutions
  5. Runs nemo-evaluator-launcher as a subprocess
  6. Normalizes raw output into output/eval_results.json  (schema: schemas/output_schema.json)
  7. Updates output/eval_status.json  →  {"status": "complete"} or {"status": "failed"}

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
from urllib.request import urlopen, Request
from urllib.error import URLError

import yaml


PIPELINES_DIR  = Path(__file__).parent / "pipelines"
DATASETS_DIR   = Path(__file__).parent / "datasets"
OUTPUT_DIR     = Path(__file__).parent / "output"
DEFAULT_DATASET = DATASETS_DIR / "sample_cases.json"


# ---------------------------------------------------------------------------
# Status file — external CLI polls this
# ---------------------------------------------------------------------------

def write_status(status: str, run_id: str, pipeline: str, endpoint: str, error: str | None = None):
    OUTPUT_DIR.mkdir(exist_ok=True)
    payload = {
        "status": status,           # submitted | running | complete | failed
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
    """Returns None on success, error string on failure."""
    base = endpoint_url.rstrip("/")
    # Try /models (standard OpenAI health signal)
    check_url = base.rstrip("/v1").rstrip("/") + "/v1/models"
    try:
        req = Request(check_url, headers={"Accept": "application/json"})
        with urlopen(req, timeout=10):
            return None
    except URLError as e:
        return f"Endpoint not reachable at {check_url}: {e.reason}"
    except Exception as e:
        return f"Endpoint check failed: {e}"


def validate_inputs(endpoint: str, pipeline: str, dataset: str) -> list[str]:
    errors = []

    error = health_check(endpoint)
    if error:
        errors.append(f"Health check failed — {error}")

    pipeline_path = PIPELINES_DIR / pipeline
    if not pipeline_path.exists():
        available = [f.name for f in PIPELINES_DIR.glob("*.yaml")]
        errors.append(
            f"Pipeline '{pipeline}' not found in pipelines/. "
            f"Available: {available or 'none'}"
        )

    if not Path(dataset).exists():
        errors.append(f"Dataset not found: {dataset}")

    return errors


# ---------------------------------------------------------------------------
# Dataset conversion: our schema → NeMo OpenAI messages JSONL
# ---------------------------------------------------------------------------

def load_dataset(path: str) -> list[dict]:
    text = Path(path).read_text()
    if path.endswith(".jsonl"):
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    return json.loads(text)


def to_nemo_jsonl(dataset: list[dict], output_path: str):
    """
    NeMo 'openai' format: one JSON object per line with:
      {"messages": [...], "ideal": "<reference or null>", "metadata": {...}}

    We embed our full case metadata so it round-trips through NeMo's report.json.
    """
    lines = []
    for case in dataset:
        record = {
            "messages": [{"role": "user", "content": case["input"]}],
            "ideal": case.get("ideal_response"),
            "metadata": {
                "id": case["id"],
                "source": case.get("source", ""),
                "expected_behavior": case.get("expected_behavior", ""),
                "notes": case.get("notes", ""),
                "input": case["input"],
            },
        }
        lines.append(json.dumps(record))
    Path(output_path).write_text("\n".join(lines))


# ---------------------------------------------------------------------------
# Pipeline YAML rendering
# Substitutes ${VAR} placeholders with runtime values.
# api_key_name stays as an env var NAME — NeMo reads the actual env var itself.
# ---------------------------------------------------------------------------

def render_pipeline(pipeline_path: Path, dataset_tmp: str, endpoint: str, nemo_output_dir: str) -> str:
    # Only runtime values are substituted — everything else (judge model, judge URL,
    # evaluation settings) is configured directly in the pipeline YAML by the user.
    agent_url = endpoint.rstrip("/")
    if not agent_url.endswith("/chat/completions"):
        agent_url += "/chat/completions"

    substitutions = {
        "OUTPUT_DIR":         str(Path(nemo_output_dir).absolute()),
        "AGENT_ENDPOINT_URL": agent_url,
        "AGENT_MODEL_NAME":   os.environ.get("AGENT_MODEL_NAME", "agent"),
        "DATASET_PATH":       str(Path(dataset_tmp).absolute()),
        "MAX_CONCURRENCY":    os.environ.get("MAX_CONCURRENCY", "4"),
        # LiteLLM proxy URL — present in the environment at execution time.
        # NeMo routes judge LLM calls through this; model name in the pipeline
        # YAML uses LiteLLM format (e.g. openai/gpt-4o-mini).
        "LITELLM_PROXY_URL":  os.environ.get("LITELLM_PROXY_URL", "http://localhost:4000/v1/chat/completions"),
    }

    text = pipeline_path.read_text()
    for key, value in substitutions.items():
        text = text.replace(f"${{{key}}}", value)
    return text


# ---------------------------------------------------------------------------
# Run nemo-evaluator-launcher
# ---------------------------------------------------------------------------

def run_nemo(rendered_yaml: str, nemo_output_dir: str) -> None:
    env = {
        **os.environ,
        "AGENT_API_KEY": os.environ.get("AGENT_API_KEY", ""),
        "JUDGE_API_KEY": os.environ.get("JUDGE_API_KEY", ""),
    }

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, prefix="nemo_pipeline_"
    ) as f:
        f.write(rendered_yaml)
        cfg_path = f.name

    try:
        result = subprocess.run(
            ["nemo-evaluator-launcher", "run", "--config", cfg_path],
            env=env,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"nemo-evaluator-launcher exited with code {result.returncode}")
    finally:
        os.unlink(cfg_path)


# ---------------------------------------------------------------------------
# Normalize NeMo output → our output schema
#
# NeMo writes to:
#   <nemo_output_dir>/artifacts/results.json   aggregate scores per task
#   <nemo_output_dir>/artifacts/report.json    per-sample request/response + judge scores
# ---------------------------------------------------------------------------

def normalize_output(nemo_output_dir: str, dataset: list[dict], endpoint: str, pipeline: str, run_id: str) -> dict:
    artifacts     = Path(nemo_output_dir) / "artifacts"
    results_path  = artifacts / "results.json"
    report_path   = artifacts / "report.json"

    dataset_by_id = {c["id"]: c for c in dataset}

    # Per-sample scores from report.json
    cases = []
    if report_path.exists():
        report  = json.loads(report_path.read_text())
        samples = report if isinstance(report, list) else report.get("samples", [])

        for s in samples:
            meta     = s.get("metadata", {})
            case_id  = meta.get("id", "unknown")
            original = dataset_by_id.get(case_id, {})

            judge_out = s.get("judge_output", {})
            if isinstance(judge_out, str):
                try:
                    judge_out = json.loads(judge_out)
                except json.JSONDecodeError:
                    judge_out = {}

            q_score  = judge_out.get("score")
            q_reason = judge_out.get("reason", "")

            cases.append({
                "id":               case_id,
                "input":            original.get("input", meta.get("input", "")),
                "expected_behavior": meta.get("expected_behavior", original.get("expected_behavior")),
                "agent_response":   s.get("response", s.get("output", "")),
                "quality_score":    q_score,
                "judge_reason":     q_reason,
                "passed":           q_score >= 0.5 if isinstance(q_score, (int, float)) else None,
                "answer_match_score": s.get("rouge_l"),
                "notes":            original.get("notes", meta.get("notes", "")),
                "source":           original.get("source", meta.get("source", "")),
            })

    # Aggregate scores from results.json
    nemo_aggregate = {}
    if results_path.exists():
        raw = json.loads(results_path.read_text())
        for task_name, task_data in raw.get("tasks", {}).items():
            for metric_name, metric_data in task_data.get("metrics", {}).items():
                for score_name, score_data in metric_data.get("scores", {}).items():
                    nemo_aggregate[f"{task_name}.{metric_name}.{score_name}"] = score_data.get("value")

    scored     = [c for c in cases if isinstance(c["quality_score"], (int, float))]
    mean_score = sum(c["quality_score"] for c in scored) / len(scored) if scored else None
    pass_rate  = sum(1 for c in scored if c["passed"]) / len(scored) if scored else None
    good       = [c for c in scored if c["expected_behavior"] == "good"]
    bad        = [c for c in scored if c["expected_behavior"] == "bad"]

    return {
        "run_id":         run_id,
        "completed_at":   datetime.now(timezone.utc).isoformat(),
        "agent_endpoint": endpoint,
        "pipeline":       pipeline,
        "total_cases":    len(dataset),
        "summary": {
            "mean_quality_score":  round(mean_score, 4) if mean_score is not None else None,
            "pass_rate":           round(pass_rate,  4) if pass_rate  is not None else None,
            "good_case_pass_rate": round(sum(1 for c in good if c["passed"]) / len(good), 4) if good else None,
            "bad_case_pass_rate":  round(sum(1 for c in bad  if c["passed"]) / len(bad),  4) if bad  else None,
            "nemo_aggregate":      nemo_aggregate,
        },
        "cases": cases,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Run NeMo Evaluator batch evaluation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--endpoint", required=True,
        help="Base URL of the agent's OpenAI-compatible API (e.g. http://localhost:8080/v1)",
    )
    parser.add_argument(
        "--pipeline", required=True,
        help="Pipeline YAML filename in pipelines/ (e.g. custom_qa_judge.yaml)",
    )
    parser.add_argument(
        "--dataset", default=str(DEFAULT_DATASET),
        help=f"Path to test case JSON file (default: {DEFAULT_DATASET})",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
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

    if args.dry_run:
        print("\nDry run — all inputs valid. Would run:")
        print(f"  nemo-evaluator-launcher run --config pipelines/{args.pipeline}")
        print(f"  Output → output/eval_results.json")
        sys.exit(0)

    # --- 2. Mark as running ---
    write_status("running", run_id, args.pipeline, args.endpoint)
    print(f"\nStatus: running  (output/eval_status.json)")

    dataset = load_dataset(args.dataset)
    print(f"Loaded {len(dataset)} test cases")

    # --- 3. Convert dataset + render pipeline ---
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False, prefix="nemo_dataset_"
    ) as f:
        dataset_tmp = f.name
    to_nemo_jsonl(dataset, dataset_tmp)

    nemo_output_dir = str(OUTPUT_DIR / "raw" / run_id)
    pipeline_path   = PIPELINES_DIR / args.pipeline
    rendered        = render_pipeline(pipeline_path, dataset_tmp, args.endpoint, nemo_output_dir)

    # --- 4. Run NeMo ---
    print(f"Running NeMo Evaluator...")
    try:
        run_nemo(rendered, nemo_output_dir)
    except RuntimeError as e:
        write_status("failed", run_id, args.pipeline, args.endpoint, error=str(e))
        print(f"ERROR: {e}", file=sys.stderr)
        os.unlink(dataset_tmp)
        sys.exit(2)
    finally:
        if Path(dataset_tmp).exists():
            os.unlink(dataset_tmp)

    # --- 5. Normalize output ---
    try:
        normalized = normalize_output(nemo_output_dir, dataset, args.endpoint, args.pipeline, run_id)
    except Exception as e:
        write_status("failed", run_id, args.pipeline, args.endpoint, error=f"Output normalization failed: {e}")
        print(f"ERROR normalizing output: {e}", file=sys.stderr)
        sys.exit(3)

    # --- 6. Write to fixed output location ---
    OUTPUT_DIR.mkdir(exist_ok=True)
    (OUTPUT_DIR / "eval_results.json").write_text(json.dumps(normalized, indent=2))
    write_status("complete", run_id, args.pipeline, args.endpoint)

    s = normalized["summary"]
    print(f"\nStatus: complete")
    print(f"Results: output/eval_results.json")
    print(f"  Total cases:        {normalized['total_cases']}")
    print(f"  Mean quality score: {s['mean_quality_score']}")
    print(f"  Pass rate:          {s['pass_rate']}")
    print(f"  Good case pass:     {s['good_case_pass_rate']}")
    print(f"  Bad case pass:      {s['bad_case_pass_rate']}")


if __name__ == "__main__":
    main()
