import json
from datetime import datetime, timezone
from pathlib import Path


def write_status(
    status: str,
    run_id: str,
    pipeline: str,
    endpoint: str,
    output_dir: Path,
    error: str | None = None,
) -> None:
    output_dir.mkdir(exist_ok=True)
    payload = {
        "status": status,  # running | complete | failed
        "run_id": run_id,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "pipeline": pipeline,
        "agent_endpoint": endpoint,
        "error": error,
    }
    (output_dir / "eval_status.json").write_text(json.dumps(payload, indent=2))
