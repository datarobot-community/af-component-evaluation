import json
import os
import sys
import tempfile
from pathlib import Path

from evaluator.dataset import load_dataset, to_byob_jsonl
from evaluator.output import normalize_output
from evaluator.runner import run_byob
from evaluator.status import write_status
from evaluator.utils import make_run_id
from evaluator.validation import load_pipeline, validate_inputs

# evaluator/ lives one level below the repo root (template/)
_DEFAULT_REPO_ROOT = Path(__file__).parent.parent


class EvalRunner:
    def __init__(
        self,
        endpoint: str,
        pipeline: str,
        dataset: str,
        repo_root: Path | None = None,
    ) -> None:
        self.endpoint = endpoint
        self.pipeline = pipeline
        self.dataset = dataset
        self.repo_root = repo_root if repo_root is not None else _DEFAULT_REPO_ROOT
        self.pipelines_dir = self.repo_root / "pipelines"
        self.output_dir = self.repo_root / "output"

    def run(self, dry_run: bool = False) -> int:
        run_id = make_run_id()

        # 1. Validate
        print("Validating inputs...")
        errors = validate_inputs(
            self.endpoint,
            self.pipeline,
            self.dataset,
            self.pipelines_dir,
            self.repo_root,
        )
        if errors:
            print("Validation failed:", file=sys.stderr)
            for e in errors:
                print(f"  ✗ {e}", file=sys.stderr)
            return 1
        print(f"  ✓ Endpoint reachable: {self.endpoint}")
        print(f"  ✓ Pipeline found:     pipelines/{self.pipeline}")
        print(f"  ✓ Dataset found:      {self.dataset}")

        cfg = load_pipeline(self.pipelines_dir / self.pipeline)

        if dry_run:
            print("\nDry run — all inputs valid. Would run BYOB benchmark:")
            print(f"  module:  {cfg['benchmark']['module']}")
            print(f"  judge:   {cfg['judge']['model_id']} @ {cfg['judge']['url']}")
            print(f"  output → output/eval_results.json")
            return 0

        # 2. Mark as running
        write_status("running", run_id, self.pipeline, self.endpoint, self.output_dir)
        print("\nStatus: running  (output/eval_status.json)")

        dataset = load_dataset(self.dataset)
        print(f"Loaded {len(dataset)} test cases")

        # 3. Convert dataset to BYOB JSONL
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False, prefix="byob_dataset_"
        ) as f:
            dataset_jsonl = f.name
        to_byob_jsonl(dataset, dataset_jsonl)

        nemo_output_dir = str(self.output_dir / "raw" / run_id)

        # 4. Run BYOB
        print("Running NeMo Evaluator (BYOB, in-process)...")
        try:
            run_byob(cfg, self.endpoint, dataset_jsonl, nemo_output_dir, self.repo_root)
        except RuntimeError as e:
            write_status(
                "failed", run_id, self.pipeline, self.endpoint, self.output_dir, error=str(e)
            )
            print(f"ERROR: {e}", file=sys.stderr)
            return 2
        finally:
            if Path(dataset_jsonl).exists():
                os.unlink(dataset_jsonl)

        # 5. Normalize output
        try:
            normalized = normalize_output(
                nemo_output_dir, dataset, self.endpoint, self.pipeline, run_id
            )
        except Exception as e:  # noqa: BLE001
            write_status(
                "failed",
                run_id,
                self.pipeline,
                self.endpoint,
                self.output_dir,
                error=f"Output normalization failed: {e}",
            )
            print(f"ERROR normalizing output: {e}", file=sys.stderr)
            return 3

        # 6. Write to fixed output locations (external CLI relies on these paths)
        self.output_dir.mkdir(exist_ok=True)
        (self.output_dir / "eval_results.json").write_text(json.dumps(normalized, indent=2))
        write_status("complete", run_id, self.pipeline, self.endpoint, self.output_dir)

        s = normalized["summary"]
        print("\nStatus: complete")
        print("Results: output/eval_results.json")
        print(f"  Total cases:        {normalized['total_cases']}")
        print(f"  Scored / inconcl.:  {s['scored_cases']} / {s['inconclusive_cases']}")
        print(f"  Mean quality score: {s['mean_quality_score']}")
        print(f"  Pass rate:          {s['pass_rate']}")
        print(f"  Good case pass:     {s['good_case_pass_rate']}")
        print(f"  Bad case pass:      {s['bad_case_pass_rate']}")

        return 0
