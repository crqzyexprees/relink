# ReLink project rules

- Build a paper-aware dataset recovery tool for HackPSU 2026.
- MVP stack: Python 3.12+, Streamlit, httpx, PyMuPDF, pytest. No React,
  separate API server, database, or paid LLM API.
- Keep UI, extraction, provider access, ranking, and verification separate.
  Providers must return shared evidence-bearing candidates; keep provider
  orchestration independent of dataset/media-specific implementations.
- Never fabricate resources, evidence, verification, or recovery success.
  A metadata match or archived page is not proof that dataset bytes survive.
- Use real service responses for live results. Automated tests must use mocked
  HTTP responses and local fixtures; live checks are explicit and separate.
- Record candidate provenance, evidence, limitations, and verification status.
  Treat no results, service failure, and unverified results as distinct outcomes.
- Bound remote requests with timeouts and resource limits. Do not commit secrets,
  uploaded papers, downloaded datasets, or local environment files.
- Make small, scoped changes. Run relevant checks before marking a milestone
  complete; report checks that could not run without implying success.
- Update STATUS.md after every milestone with progress, decisions, blockers,
  verification evidence, and next steps. Follow PLAN.md; do not implement later
  milestones without authorization.
- Run commands from the project root using `.venv/bin/python`. Future tests:
  `.venv/bin/python -m pytest`. Keep dependency declarations current.
