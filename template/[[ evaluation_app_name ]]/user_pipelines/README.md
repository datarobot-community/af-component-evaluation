# Pipelines

A **pipeline** is a small YAML that wires a benchmark to the agent under test
(and, for judge-based benchmarks, to a judge model). The files here are
**defaults, not examples**: pick the one that measures what you want, point
`--dataset` at your data, and run.

```bash
task eval -- \
  --endpoint http://localhost:8842/v1 \
  --pipeline answer_quality.yaml \
  --dataset  user_datasets/sample_answer_quality.json
```

8 default pipelines ship here (3 judge-based, 5 judge-free), each with a matching
`user_datasets/sample_<name>.json`. The `user_example_*` files are copy-me
templates for writing your own benchmark + pipeline.

**Full documentation** (the 8-benchmark menu, YAML schema, model-naming rules, and
how to author your own) lives in **`docs/evaluation/`**:

- [`pipelines.md`](../../docs/evaluation/pipelines.md) — pipeline YAML format + the benchmark menu
- [`benchmarks.md`](../../docs/evaluation/benchmarks.md) — what each benchmark measures and how it scores
- [`writing-benchmarks.md`](../../docs/evaluation/writing-benchmarks.md) — author a custom benchmark + pipeline
- [`datasets.md`](../../docs/evaluation/datasets.md) — dataset schema and per-benchmark fields
