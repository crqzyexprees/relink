# ReLink Implementation Plan

**Goal:** Help researchers find and evaluate surviving dataset candidates from
a missing URL or research paper, with traceable evidence and honest status.

**Architecture:** A local Streamlit app calls modular Python functions. Extraction
produces links and paper context; independent providers return candidates with
provenance; ranking explains relevance; verification reports what was checked.
Future media-specific providers can use the same candidate contract without
changing the UI or ranking orchestration. No plugin framework is needed yet.

**Stack:** Python 3.12+, Streamlit, httpx, PyMuPDF, pytest.
**Requirements:** The user-provided HackPSU 2026 brief, captured below.
**Execution:** Work milestone by milestone, with relevant checks and STATUS.md
updates at each boundary. The follow-up request authorizes the URL-only Internet
Archive feature below; PDF extraction and all additional providers remain deferred.

## Current authorized slice — URL recovery

1. Repair dependencies where local resources permit and initialize usable Git
   metadata. Record sandbox restrictions rather than claiming a full install.
2. Write offline tests first for public-address validation, DNS failures, pinned
   connections, redirects, status codes, timeouts, rate limits, archive response
   parsing, and orchestration. Use HTTPX MockTransport and mocked DNS only.
3. Add shared dataclasses in `relink/models.py`, a public-only HTTP client in
   `relink/network.py`, status checks in `relink/verification.py`, an availability
   API adapter in `relink/providers/internet_archive.py`, and `recover_url` in
   `relink/recovery.py`. Add `scripts/recover_url.py` as a JSON CLI.
4. Use bounded DNS/HTTP timeouts, five redirects maximum, public DNS answers only,
   connection pinning, preserved TLS hostname verification, and no environment
   proxies. Return Retry-After and do not automatically retry 429 responses.
5. Run the full offline suite, try a legitimate public URL live, and document
   each outcome separately in STATUS.md. No capture replay or dataset-byte
   verification is part of this slice.

**Acceptance:** Public URLs produce distinct current-access and archive outcomes.
Only a valid availability API response can create a candidate; an empty response
is not-found, and network/API failures stay failures. Unsafe targets and redirects
are blocked. Every candidate retains source and capture timestamp and explicitly
states that dataset preservation is unverified. No frontend or other provider.

**Current outcome:** Implementation and 26 offline tests pass using the unittest
runner. Pytest execution and successful live service access remain blocked by
the environment; see STATUS.md. Full M1, M3, and M4 remain incomplete.

## Scope and module map

Accept a missing HTTP(S) URL or PDF; extract research links and nearby context;
search Internet Archive and DataCite; rank and explain candidates; show evidence
and verification status in Streamlit; evaluate on real broken links.

| Path | Responsibility |
| --- | --- |
| `app.py` | Streamlit entry point; placeholder until the UI milestone |
| `relink/models.py` | Shared input, context, candidate, evidence, and status types |
| `relink/network.py` | Public-only DNS/HTTP, pinned connections, redirects, request limits |
| `relink/extraction.py` | URL/PDF parsing and surrounding research context |
| `relink/providers/` | Independent Internet Archive and DataCite adapters |
| `relink/recovery.py` | Provider orchestration and partial-failure handling |
| `relink/ranking.py` | Deterministic scoring and readable reasons |
| `relink/verification.py` | Evidence-based access and identity checks |
| `tests/` | Offline tests with local fixtures and mocked service responses |
| `docs/` | Manual live evaluation protocol and recorded observations |

## Milestones and acceptance criteria

### M0 — Repository and environment foundation

- [x] Inspect files and available Python/dependency tooling.
- [x] Add AGENTS.md, PLAN.md, STATUS.md, README.md, requirements.txt,
  .gitignore, and placeholder modules/directories.
- [x] Create an isolated environment and attempt dependency installation.
- [x] Check syntax, imports, dependency health, and absence of recovery logic.
  Document unavailable checks and environment blockers precisely.

**Acceptance:** A documented modular scaffold exists, environment readiness is
reported from actual commands, and no extraction, recovery, ranking, or UI
functionality is implemented.

### M1 — Inputs, shared contracts, and paper context

- [ ] Define shared types in `relink/models.py` before provider implementation.
  Candidates carry source, original URL, candidate URL, metadata, retrieval
  timestamp, evidence, and verification status. Provider outcomes distinguish
  success, empty results, and failure.
- [ ] Implement URL validation and PDF extraction in `relink/extraction.py`.
  Extract text URLs and hyperlink annotations, deduplicate, and retain page
  numbers and nearby text. Preserve original URLs alongside normalized values.
- [ ] Add `tests/test_extraction.py` and `tests/test_models.py` with local PDF
  fixtures for annotations, wrapped/punctuated links, duplicates, malformed and
  encrypted PDFs, and PDFs without extractable text.

**Acceptance:** A URL or text-readable PDF yields structured context, or a clear
input limitation. Scanned PDFs do not silently appear successfully extracted.
Offline tests pass: `.venv/bin/python -m pytest tests/test_extraction.py tests/test_models.py`.

### M2 — Internet Archive provider

- [x] Implement `relink/providers/internet_archive.py` using httpx and the shared
  provider contract; retain original URLs and capture timestamps.
- [x] Add archive tests in `tests/test_url_recovery.py` using mocked HTTP responses
  for valid captures, no captures, timeouts, rate limits, and malformed data.
  Availability returns one closest capture; duplicate capture lists do not
  arise in this adapter.

**Acceptance:** Actual captures become provenance-bearing candidates. An archived
HTML landing page is never labeled a recovered dataset. Offline provider tests
pass; an explicitly run live smoke check records its actual outcome separately.

### M3 — DataCite provider and orchestration

- [ ] Implement `relink/providers/datacite.py` using URL and available paper
  context; preserve DOI, titles, creators, publisher, dates, and related IDs.
- [ ] Implement `relink/recovery.py` against a common provider interface; a
  provider failure must not discard another provider's usable results.
- [ ] Add `tests/test_datacite.py` and `tests/test_recovery.py` for sparse metadata,
  empty results, pagination limits, rate limits, timeouts, and partial failures.

**Acceptance:** Both providers return compatible candidates and distinct error
states. DataCite metadata alone never establishes file availability. Mocked
provider/orchestration tests pass without network access.

### M4 — Explainable ranking and verification

- [ ] Implement `relink/ranking.py` with deterministic signals: exact URL/DOI,
  title/context overlap, creator overlap, and relevant dates. Expose each signal
  and its contribution; scores describe relevance, not calibrated probability.
- [ ] Implement bounded checks in `relink/verification.py`. Distinguish unverified,
  metadata-only, accessible landing page, accessible file, unavailable, and
  inconclusive checks. Track identity evidence independently of accessibility.
- [ ] Add `tests/test_ranking.py` and `tests/test_verification.py` for ties, missing
  metadata, conflicting identity, redirects, HTML masquerading as a file, HTTP
  errors, and request limits. Apply public-URL validation to redirected requests.

**Acceptance:** Every result explains why it ranks and what verification proves.
Accessibility alone never proves that bytes match the original study's dataset.
Mocked ranking/verification tests pass deterministically.

### M5 — Streamlit workflow

- [ ] Implement `app.py` with URL/PDF input, explicit search action, progress,
  ranked candidates, evidence, source links, and verification limitations.
- [ ] Keep network calls in providers/services and avoid duplicate searches on
  unrelated UI reruns. Bound input size, result count, and request duration.
- [ ] Add `tests/test_app.py` using mocked recovery calls and Streamlit's test
  harness for URL/PDF flows, invalid inputs, empty results, and partial failures.

**Acceptance:** Users can complete both input paths and distinguish a candidate
from a verified resource. Offline UI tests pass and a local manual smoke check
confirms the flow with real responses.

### M6 — Real broken-link evaluation

- [ ] Add `docs/evaluation.md` with at least five public research dataset links,
  paper citations where available, selection rationale, check timestamps, and
  observed original-link HTTP outcomes. Include unrecovered examples.
- [ ] Run live checks separately from pytest. Record candidates, evidence,
  verification status, failures, and manual relevance judgments; do not choose
  only successful cases or equate provider outages with absent resources.
- [ ] Document demo steps and limitations; rerun the complete offline test suite.

**Acceptance:** At least five real cases have reproducible inputs and dated,
honest outcomes. The demo works even when no recoverable dataset is found.

## Review focus

Untrusted URLs and redirects (M1/M4); unsupported PDFs (M1); provider outages and
rate limits (M2/M3); similar titles but wrong dataset identity (M4); landing pages
mistaken for files (M2/M4). Each is covered in its owning milestone's tests.

## Out of scope

React, separate API servers, databases, user accounts, paid LLM APIs, OCR,
automatic full-dataset downloads, background crawling, bypassing authentication
or access restrictions, guaranteed recovery, scientific reproducibility claims,
and implemented media-specific providers. Retain architectural room for those
providers without building them in the MVP.
