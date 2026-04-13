#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/source_local_env.sh"

python -m uvicorn services.api.app.main:app --reload --host 127.0.0.1 --port "${PORT:-8000}"

