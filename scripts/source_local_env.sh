#!/usr/bin/env bash

if [ -n "${BASH_VERSION:-}" ]; then
    _travel_this_file="${BASH_SOURCE[0]}"
elif [ -n "${ZSH_VERSION:-}" ]; then
    _travel_this_file="${(%):-%N}"
else
    _travel_this_file="$0"
fi

TRAVEL_SCRIPT_DIR="$(cd "$(dirname "$_travel_this_file")" && pwd)"
TRAVEL_PROJECT_ROOT="$(cd "${TRAVEL_SCRIPT_DIR}/.." && pwd)"
TRAVEL_SHARED_PROVIDER_ROOT="${TRAVEL_SHARED_PROVIDER_ROOT:-/home/renancatan/renan/projects/agentic_warehouse_analytics_copilot/aws_analytics_copilot}"

TRAVEL_AWS_ACTIVATE="${TRAVEL_SHARED_PROVIDER_ROOT}/scripts/activate_personal_aws.sh"
TRAVEL_LLM_ACTIVATE="${TRAVEL_SHARED_PROVIDER_ROOT}/scripts/activate_gemini_api.sh"

if [ -f "${TRAVEL_AWS_ACTIVATE}" ]; then
    # shellcheck disable=SC1090
    source "${TRAVEL_AWS_ACTIVATE}"
    echo "AWS env loaded from ${TRAVEL_AWS_ACTIVATE}"
else
    echo "Warning: AWS activation script not found at ${TRAVEL_AWS_ACTIVATE}"
fi

if [ -f "${TRAVEL_LLM_ACTIVATE}" ]; then
    # shellcheck disable=SC1090
    source "${TRAVEL_LLM_ACTIVATE}"
    echo "LLM env loaded from ${TRAVEL_LLM_ACTIVATE}"
else
    echo "Warning: LLM activation script not found at ${TRAVEL_LLM_ACTIVATE}"
fi

if [ -f "${TRAVEL_PROJECT_ROOT}/.venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "${TRAVEL_PROJECT_ROOT}/.venv/bin/activate"
    echo "Local travel .venv activated."
elif [ -f "${TRAVEL_SHARED_PROVIDER_ROOT}/.venv/bin/activate" ]; then
    # shellcheck disable=SC1090
    source "${TRAVEL_SHARED_PROVIDER_ROOT}/.venv/bin/activate"
    echo "Shared provider .venv activated from ${TRAVEL_SHARED_PROVIDER_ROOT}/.venv."
else
    echo "Warning: no Python virtualenv found in this repo or shared provider repo."
fi

export APP_ENV="${APP_ENV:-development}"
export APP_BASE_URL="${APP_BASE_URL:-http://127.0.0.1:3000}"
export API_BASE_URL="${API_BASE_URL:-http://127.0.0.1:8000}"
export COPILOT_DEFAULT_MODEL_ALIAS="${COPILOT_DEFAULT_MODEL_ALIAS:-ggl2}"
export PYTHONPATH="${TRAVEL_PROJECT_ROOT}:${PYTHONPATH:-}"

cd "${TRAVEL_PROJECT_ROOT}" || return 1
echo "Changed directory to ${PWD}"
echo "COPILOT_DEFAULT_MODEL_ALIAS=${COPILOT_DEFAULT_MODEL_ALIAS}"
echo "API_BASE_URL=${API_BASE_URL}"

