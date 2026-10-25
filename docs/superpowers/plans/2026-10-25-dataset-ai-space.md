# Dataset AI and space UI implementation plan

**Spec:** ../specs/2026-10-25-dataset-ai-space-design.md, explicitly owner-authorized.
**Approach:** TDD, modular service integration; independent preview and CSS domains
can run in parallel. Parent owns shared workflow/UI integration and final review.

1. Dataset preview contracts and safe streaming samples.
   Files: dataset_models.py, dataset_preview.py, network.py, tests/test_dataset_preview.py.
   Preview records expose status/url/time/header/rows/bytes/detail/truncated and
   selected response metadata. Cap64KiB,3 rows,3 candidates; public-only redirects.
2. Evidence-grounded dataset reranking and combined orchestration.
   Files: providers/gemini_datasets.py, dataset_ai.py, models.py, recovery.py,
   workflow.py, gemini_models.py, papers.py, gemini.py; new mocked provider/flow tests.
   Preserve scores/statuses, force identity/conflict tiers, add backwards-compatible
   AI fields and one assessment for each combined batch. No live key in tests.
3. Thin native UI integration and space theme.
   Files: dataset_ui.py, ui.py, paper_ui.py, gemini_ui.py, history_ui.py,
   theme.py, .streamlit/config.toml; AppTests and history round trips.
   All remote content stays plain text/JSON/native cells. Cached Load more never
   makes provider/model calls. Fresh requests preserve identity guards.
4. Full verification, live services, review, docs/status and scoped commits/push.

- [x] Preview/streaming tests RED→GREEN and independent checks.
- [x] Dataset AI ordering/identity/fallback tests RED→GREEN.
- [x] UI flows/theme/history integration and relevant checks.
- [x] Full suite, real public checks, fresh read-only review and documented limits.
- [ ] Update STATUS after milestones, commit/push under prior authorization.

Review focus: sample data bounds/partial rows; credentials and SSRF on redirects;
model ID/reference validation; exact identity/version/hash order; no silent
source/AI failure; current/legacy history privacy; fresh versus cached controls.

Final checks:269 tests/192 subtests pass. Actual public three-row CSV+Gemini and
separate exact Iris DOI+Gemini checks pass. Initial broad query weak leads remain
recorded. Fresh review findings (initial identity evidence loss and missing paper
sample disclosure) were reproduced RED, fixed GREEN and followed by the full suite.
Original CSS/theme has no new assets/dependencies; physical browser review remains
unavailable. Earlier implementation milestone/status is recorded in STATUS.md.
