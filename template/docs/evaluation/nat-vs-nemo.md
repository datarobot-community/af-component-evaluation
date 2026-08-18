# NAT `/evaluate` vs. this component

Two different tools solve different problems at different layers. Both use the word "evaluate," but they test different aspects of an agent.

## Quick reference

| | NAT `/evaluate` | This component (NeMo Evaluator BYOB) |
|---|---|---|
| **What it tests** | Agent *behavior*&mdash;trajectories, tool use, RAG grounding. | Agent *outputs*&mdash;correctness, safety, quality at scale. |
| **Perspective** | Inside-out: NAT runs your workflow and observes it. | Outside-in: hits the agent endpoint as a black box. |
| **Trigger** | `POST /evaluate` on the NAT server, or `nat eval` CLI. | `run.py` (via the core CLI or `task eval`). |
| **Knows about agent internals?** | Yes&mdash;sees tool calls, intermediate steps, which nodes ran. | No&mdash;only sees the final response. |
| **Metrics** | RAGAS (AnswerAccuracy, ContextRelevance, Groundedness), trajectory judging. | LLM-as-judge plus deterministic checks across 8 benchmarks. |
| **Where config lives** | The agent repo (alongside the workflow). | This component (`user_pipelines/` + `user_datasets/`). |
| **Best for** | Interactive playground testing, checking whether the agent *reasoned correctly*. | Batch regression testing, safety checks, comparing agent versions. |

## NAT `/evaluate`&mdash;the right tool for

**Use NAT `/evaluate` when you are in the playground and want to understand agent behavior.**

- Did the agent use the correct tools in the right order?
- Is the RAG pipeline retrieving relevant context?
- Is the reasoning trajectory sound, or is it hallucinating intermediate steps?
- "The agent gave the right answer&mdash;but did it get there correctly?"

It is baked into the NAT server and triggered by a REST call or CLI command against a running NAT deployment. It is tightly coupled to your specific workflow. Config and datasets that test *that specific agent's workflow* live alongside the agent code.

## This component&mdash;the right tool for

**Use this component when you want to batch-test agent outputs across many cases.**

- Does the agent produce correct, safe, appropriate responses at scale?
- Does it refuse harmful requests? Does it stay grounded in provided context?
- After an LLM upgrade, did the agent regress on any known-good cases?
- "We have 50 test cases&mdash;run them all, score every response, tell me what broke."

It treats the agent as a black box. It only sees what an end user would see&mdash;the final response. It does not know or care about LangGraph, tools, or NAT internals, which is why it can point at *any* agent endpoint and be reused across projects.

## The mental model

Think of it like software testing layers:

```
NAT /evaluate    →   Integration test (tests the workflow internals)
This component   →   End-to-end / regression test (tests the user-facing output)
```

Neither replaces the other. A mature setup uses both:

1. **During development**&mdash;NAT `/evaluate` in the playground to verify reasoning.
2. **Before release or on a schedule**&mdash;a batch run from this component to catch regressions in output quality.

## See also

- [Getting started](./getting-started.md)&mdash;run this component end to end.
- [Benchmarks](./benchmarks.md)&mdash;what each built-in benchmark measures.
