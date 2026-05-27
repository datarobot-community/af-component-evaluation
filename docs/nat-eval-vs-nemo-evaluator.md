# NAT Evaluate vs. NeMo Evaluator — When to Use Each

Two different tools, two different jobs. Both use the word "evaluate" but they solve different problems at different layers.

---

## Quick Reference

| | NAT `/evaluate` | NeMo Evaluator (standalone) |
|---|---|---|
| **What it tests** | Agent *behavior* — trajectories, tool use, RAG grounding | Agent/LLM *outputs* — correctness, safety, quality at scale |
| **Perspective** | Inside-out: NAT runs your workflow and observes it | Outside-in: hits the agent endpoint as a black box |
| **Trigger** | `POST /evaluate` on the NAT server, or `nat eval` CLI | `nemo-evaluator-launcher run` CLI or Docker |
| **Dataset** | YAML config + JSON dataset, run by the NAT server | JSON/JSONL dataset, run by the evaluator process |
| **Metrics** | RAGAS (AnswerAccuracy, ContextRelevance, Groundedness), Trajectory (LLM-as-judge on the agent's step-by-step path), LangSmith evaluators | LLM-as-judge, ROUGE, exact match, 100+ standard benchmarks (MMLU, HumanEval, etc.) |
| **Knows about agent internals?** | Yes — sees tool calls, intermediate steps, which nodes ran | No — only sees the final response |
| **Where it lives** | Built into the NAT server; config can live in the agent repo | Separate tool; config + datasets live in `af-component-evaluation` |
| **Best for** | Interactive playground testing, checking whether the agent *reasoned correctly* | Batch regression testing, safety checks, comparing agent versions |

---

## NAT `/evaluate` — The Right Tool For

**Use this when you're in the playground and want to understand agent behavior.**

- Did the agent use the correct tools in the right order?
- Is the RAG pipeline retrieving relevant context?
- Is the agent's reasoning trajectory sound, or is it hallucinating intermediate steps?
- "The agent gave the right answer — but did it get there correctly?"

This is baked into the NAT server. You trigger it with a REST call or CLI command against a running NAT deployment. It's tightly coupled to your specific workflow — it knows the agent's internal structure.

**Example scenario:** You updated the planner node's system prompt. You want to verify the trajectory still makes sense for a set of 10 example queries. You run `POST /evaluate` on the dev NAT server with a YAML config pointing at those 10 queries. NAT runs the full LangGraph workflow for each one, records the trajectory, and a judge LLM scores whether each step made sense.

**Where to add it:** The agent repo (`recipe-datarobot-agent-application/agent/`) — evaluation config and datasets that test *that specific agent's workflow* live alongside the agent code.

---

## NeMo Evaluator (Standalone) — The Right Tool For

**Use this when you want to batch-test agent outputs across many cases.**

- Does the agent produce correct, safe, appropriate responses at scale?
- Does it refuse harmful requests? Does it stay on topic?
- After an LLM upgrade, did the agent regress on any known-good cases?
- "We have 50 test cases — run them all, score every response, tell me what broke."

This is a separate process that treats the agent as a black box. It only sees what an end user would see — the final response. It doesn't know or care about LangGraph, tools, or NAT internals.

**Example scenario:** You collected 30 real agent interactions from users — some good, some bad — and used Claude to generate 20 more edge cases. You want to run all 50 through the current deployed agent and get a quality score for each. You set `AGENT_ENDPOINT_URL` to the DataRobot deployment URL, run `./scripts/run_eval.sh`, and get a `results.json` with per-sample scores.

**Where it lives:** `af-component-evaluation/` — a separate workspace that can point at *any* agent endpoint, making it reusable across multiple agent projects.

---

## The Mental Model

Think of it like software testing layers:

```
NAT /evaluate         →   Integration test (tests the workflow internals)
NeMo Evaluator        →   End-to-end / regression test (tests the user-facing output)
```

Neither replaces the other. A mature setup uses both:
1. **During development** — NAT `/evaluate` in the playground to verify agent reasoning
2. **Before release / on a schedule** — NeMo Evaluator batch run to catch regressions in output quality

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────┐
│  PLAYGROUND / DEVELOPMENT                               │
│                                                         │
│  NAT Server ──► /evaluate endpoint                      │
│       │                                                 │
│       ▼                                                 │
│  Runs LangGraph workflow internally                     │
│  Scores trajectories + RAG quality                      │
│  Config lives in: agent repo (eval/)                    │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│  BATCH TESTING / REGRESSION / RELEASE GATE              │
│                                                         │
│  React UI ──► FastAPI server ──► nemo-evaluator-launcher│
│                                       │                 │
│                                       ▼                 │
│                              Agent endpoint (black box) │
│                              Scores outputs at scale    │
│                              results.json ──► React UI  │
│  Config + datasets live in: af-component-evaluation/    │
└─────────────────────────────────────────────────────────┘
```
