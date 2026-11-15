# Release progress (v0.9.0)

This snapshot identifies itself as **FieldShift 0.9.0** in `README.md` and `backend/app/config.py`. Release preparation is in progress; the notes below distinguish existing verification from checks still needed for a release candidate.

| Area | Status | Evidence / next action |
|---|---|---|
| Product changes | Implemented in this snapshot | Layout and photo lookup changes are listed in `CHANGELOG.md`; no additional code changes were made during this release-doc pass. |
| Prior automated checks | Passed for v0.8 code | `VERIFICATION.md` records 171 real pytest tests, 4 Node tests, and 6 Chromium tests for the v0.8 build. These results do not verify the v0.9 layout/media changes. |
| v0.9 regression checks | Passed directly in Windows PowerShell | 171 Python tests, 4 Node tests, syntax checks for 35 JS files and 6 Chromium tests passed. `run_tests.sh` could not start because Bash is unavailable; see `VERIFICATION.md`. |
| Live providers and app | Unverified | Start the real FastAPI app and run `python scripts/smoke.py <url>`; provider warnings depend on upstream availability. |
| Deployment and container | Unverified | Build the Docker image, deploy to the chosen host, and record the actual URL and health response. |
| Submission materials | Drafted, metadata aligned | Challenge, team and project details are in `SUBMISSION.md`; capture real screenshots/video from a deployed instance before submission. |
| Git release artifact | Not available in this folder | This directory has no `.git` metadata, so a commit, tag, or GitHub release cannot be prepared from this snapshot. |

See `VERIFICATION.md` for historical evidence and limits, `KNOWN_LIMITATIONS.md` for product caveats, and `DEPLOY.md` for deployment steps.
