import json
from pathlib import Path
from typing import Any


def load_dataset(path: str) -> list[dict[str, Any]]:
    text = Path(path).read_text()
    if path.endswith(".jsonl"):
        return [json.loads(line) for line in text.splitlines() if line.strip()]
    result: list[dict[str, Any]] = json.loads(text)
    return result


def to_byob_jsonl(dataset: list[dict[str, Any]], output_path: str) -> None:
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
