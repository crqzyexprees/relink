# ReLink project rules

- Build a paper-aware dataset recovery tool for HackPSU 2026.
- MVP stack: Python 3.12+, Streamlit, httpx, PyMuPDF, pytest. No React,
  separate API server, database, or paid LLM API.
- Keep UI, extraction, provider access, ranking, and verification separate.
- History defaults to private OIDC accounts via Streamlit auth. Authorize every
  operation using the trusted issuer/subject and current token expiry, never
  email, form/query input or caller paths. Recheck identity after remote work.
  Never assign legacy shared history automatically. Explicit local mode is only
  for a trusted single operator. Private exports must not use public media URLs.
- Owner-authorized Gemini is core to paper/PDF dataset identification on explicit
  Find actions. Use the configured free-tier project; no billing upgrades. Ground
  names/versions in actual page text, then query real repository providers. Model
  output must never create resource URLs, hashes, or verification claims. Keep
  independent recovery working on missing credentials, quota limits, or errors.
- Paper discovery uses OpenAlex/arXiv (15 records each, up to 30 unique per batch)
  with abstract-only Gemini ordering and validated own-paper passage references.
  Display actual source text; do not accept model-generated ranking quotations. Load more
  reveals cached tens without requests; explicit new batches remain separately
  ranked, exclude prior identities, and stop after three. Preserve keyword fallback
  and source failures. Serialize arXiv API calls at least three seconds apart.
- Owner-authorized dataset AI combines real metadata and bounded advertised
  CSV/TSV samples with existing evidence. At most three file attempts,64KiB each,
  header+three complete rows; unsupported formats use metadata only. One model
  assessment per combined batch, own-candidate evidence IDs, no model URLs or
  verification claims. Preserve prior URL/DOI/hash evidence across PDF merges and
  version warnings, with disclosure before processing. Cached pagination does
  not make requests. Use original code-native space styling without remote assets.
- Original ReLink code is AGPL-3.0-only. Preserve LICENSE/NOTICE and third-party
  terms. Public deployments must offer corresponding release source to users;
  configure RELINK_SOURCE_URL and verify its accessibility before deployment.
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
