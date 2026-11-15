# Audit (baseline of v0.4 and reproduction of D1–D7)
Baseline: tests could not import (`httpx` missing); server not started (no installs). Findings from reading the code (`git show 698cc01:backend/main.py`):
- D1 `combine_score` adds `priorities["profit"] * 50` (main.py ~L293). Repro in `tests/test_engine_scoring.py::test_d1_*` and `test_providers_services.py::test_d1_*`.
- D2 `/api/assistant` reads `x-forwarded-for` unconditionally (~L513); `ASSISTANT_CALLS` is a module dict; `ExplainIn.context` unbounded. Tests: `test_core_security.py::test_d2_*`.
- D3 `suitability()` feeds one day's temperature + 14-day rain to a model; `train_model.py` used a random split. Removed.
- D4 constants and 11 crops embedded in code with no sources → `crops.json`.
- D5 ~22 `innerHTML` uses in `app.js` with manual `esc()`. Now zero; see tests.
- D6 main.py 809 lines; app.js 426 dense lines → modules.
- D7 no API/isolation/frontend tests → added (API layer itself still unrun; see VERIFICATION.md).
