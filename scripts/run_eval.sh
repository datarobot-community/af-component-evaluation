#!/usr/bin/env bash
# Run NeMo Evaluator against the agent endpoint.
#
# Usage:
#   ./scripts/run_eval.sh [config_file]
#
# Required env vars:
#   AGENT_ENDPOINT_URL  - e.g. http://localhost:8080/v1
#   AGENT_API_KEY       - API key for the agent endpoint
#   AGENT_MODEL_NAME    - Model name the endpoint expects
#   JUDGE_ENDPOINT_URL  - OpenAI-compatible judge LLM endpoint
#   JUDGE_API_KEY       - API key for the judge LLM
#   JUDGE_MODEL_NAME    - e.g. meta/llama-3.1-70b-instruct

set -euo pipefail

CONFIG="${1:-configs/eval_config.yaml}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="results/${TIMESTAMP}"

# Validate required env vars
REQUIRED_VARS=(AGENT_ENDPOINT_URL AGENT_API_KEY AGENT_MODEL_NAME JUDGE_ENDPOINT_URL JUDGE_API_KEY JUDGE_MODEL_NAME)
MISSING=()
for var in "${REQUIRED_VARS[@]}"; do
  [[ -z "${!var:-}" ]] && MISSING+=("$var")
done
if [[ ${#MISSING[@]} -gt 0 ]]; then
  echo "Error: missing required env vars: ${MISSING[*]}"
  echo "See configs/eval_config.yaml for descriptions of each variable."
  exit 1
fi

echo "Config:     $CONFIG"
echo "Output dir: $OUTPUT_DIR"
echo "Agent:      $AGENT_ENDPOINT_URL"
echo "Judge:      $JUDGE_MODEL_NAME @ $JUDGE_ENDPOINT_URL"
echo ""

nemo-evaluator-launcher run \
  --config "$CONFIG" \
  --output-dir "$OUTPUT_DIR"

echo ""
echo "Results written to $OUTPUT_DIR"
echo "Summarize with: python scripts/summarize_results.py $OUTPUT_DIR"
