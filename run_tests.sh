#!/usr/bin/env bash
# Runs every mandatory check. Exits non-zero if ANY step fails (no pipes, no `|| true`).
set -euo pipefail
cd "$(dirname "$0")"
PY="${PYTHON:-python3}"
echo "== python: backend unit/integration/security/provider(mock) tests"
"$PY" -m pytest -q tests --ignore=tests/frontend
echo "== node: syntax check of every frontend module"
for f in $(find frontend -name '*.js' -not -path '*/node_modules/*'); do node --check "$f"; done
echo "== node: frontend unit tests (escape helper, no raw innerHTML)"
node --test tests/frontend/html.test.mjs
echo "== chromium: browser tests against the stand-in API (needs playwright + chromium)"
"$PY" -m pytest -q tests/frontend/test_browser.py
echo "ALL MANDATORY TESTS PASSED"
