import os
import subprocess
import sys
from pathlib import Path
from typing import Any


def run_byob(
    cfg: dict[str, Any],
    endpoint: str,
    dataset_jsonl: str,
    output_dir: str,
    repo_root: Path,
) -> None:
    benchmark = cfg["benchmark"]
    target = cfg["target"]
    judge = cfg["judge"]
    run = cfg.get("run", {})

    module_path = str((repo_root / benchmark["module"]).absolute())

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
        "--benchmark-module",
        module_path,
        "--benchmark-name",
        str(benchmark["name"]),
        "--dataset",
        dataset_jsonl,
        "--model-type",
        str(target.get("model_type", "chat")),
        "--model-url",
        endpoint,
        "--model-id",
        str(target.get("model_id", "datarobot-agent")),
        "--output-dir",
        output_dir,
        "--save-predictions",
        "--parallelism",
        str(run.get("parallelism", 4)),
        "--max-tokens",
        str(run.get("max_tokens", 1024)),
        "--temperature",
        str(run.get("temperature", 0.0)),
        "--timeout-per-sample",
        str(run.get("timeout_per_sample", 180)),
    ]

    # Only pass the target API key name if that env var is actually set. A local
    # DRUM agent needs no auth; the runner errors if the name is given but unset.
    target_key_name: str | None = target.get("api_key_name")
    if target_key_name and os.environ.get(target_key_name):
        cmd += ["--api-key-name", str(target_key_name)]

    result = subprocess.run(cmd, env=env, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"BYOB runner exited with code {result.returncode}")
