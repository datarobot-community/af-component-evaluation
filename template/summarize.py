#!/usr/bin/env python3
"""
Pretty-print a normalized eval_results.json from a completed run.

Usage:
    python summarize.py output/
    python summarize.py output/eval_results.json
"""

import sys
from pathlib import Path

from evaluator.summarize import ResultsSummarizer


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    path = Path(sys.argv[1])
    if not path.exists():
        print(f"Error: {path} does not exist")
        sys.exit(1)
    ResultsSummarizer(path).print_summary()


if __name__ == "__main__":
    main()
