# ReLink Implementation Plan

**Goal:** Help researchers find and evaluate surviving dataset candidates from
a missing URL or research paper, with traceable evidence and honest status.

**Architecture:** A local Streamlit app calls modular Python functions. Extraction
produces links and paper context; independent providers return candidates with
provenance; ranking explains relevance; verification reports what was checked.
Future media-specific providers can use the same candidate contract without
changing the UI or ranking orchestration. No plugin framework is needed yet.

**Stack:** Python 3.12+, Streamlit, httpx, PyMuPDF, pytest.
**Current owner-authorized paper upgrade:** Retrieve up to 30 unique papers per
batch from OpenAlex/arXiv, Gemini ranking on actual abstract excerpts with strict
ID/quote checks, keyword fallback, ten-at-a-time cached Load more and explicit
separately ranked next batches (three maximum). Reuse selected-paper dataset
lookup; preserve source/history isolation. See
docs/superpowers/plans/2026-10-25-paper-reranking.md and docs/PAPERS.md.
**Owner-authorized history isolation:** Use native Streamlit OIDC and separate
issuer/subject namespaces for every saved-history operation. Guests can search
without disk persistence. Keep legacy shared records untouched and require explicit
local mode for a single operator. No database/password system; see
docs/superpowers/plans/2026-10-25-history-isolation.md and docs/AUTH.md.
**Owner-authorized core AI:** Gemini is part of the paper-to-dataset workflow on
explicit Find actions, not a separate optional toggle. Validate supporting quotes
against actual extracted text; discover resources through real providers. Keep
missing-key/quota failures honest and retain independent recovery/verification.
See docs/superpowers/plans/2026-10-25-gemini-core.md.
**Owner-authorized history:** Preserve searches across browser closure/restart
using bounded local JSON snapshots, with view/rerun/delete/clear/export controls
and explicit shared-workspace scope (superseded by isolated OIDC mode above). No database; see
docs/superpowers/plans/2026-10-25-persistent-history.md and docs/HISTORY.md.
**Owner-authorized extension:** Two tabs, Find datasets and Find papers. Topic/
description search ranks papers on abstract keywords and allows selected-paper
dataset lookup. See docs/superpowers/plans/2026-10-25-paper-discovery.md. OpenAlex
paper retrieval is authorized alongside existing recovery providers; no paid LLM.
**Requirements:** The user-provided HackPSU 2026 brief, captured below.
**Execution:** Work milestone by milestone, with relevant checks and STATUS.md
updates at each boundary. The follow-up request authorizes the URL-only Internet
Archive feature below. The subsequent request also authorizes DataCite discovery,
shared candidates, deduplication, evidence-based ranking, and match statuses.
The latest request authorizes reusable PDF link extraction and the Streamlit
frontend below. Providers beyond Archive/DataCite remain deferred.

## Final readiness review — 2026-10-24

**Owner-authorized follow-up:** Adopt AGPL-3.0-only for original ReLink code,
retain PyMuPDF, add LICENSE/NOTICE and app source/license information, and find
real evaluation examples. Configure the actual source URL before deployment;
do not publish a repository or fabricate its address. Live example reports remain
separate from mocked tests and never supply production fallback candidates.

- [x] Re-read project rules and current state; run the complete suite.
- [x] Attempt live Archive, DataCite, public valid/404 URLs, and a real paper.
  All were blocked at DNS; no success or not-found result was substituted.
- [x] Verify malformed PDFs, rate limits, timeouts, empty results, rendering,
  export, ranking, and absence of sample-result fallbacks with mocked tests.
- [x] Fix DOI resolver URL search integration with failing-then-passing tests;
  retain DataCite rights metadata and correct the PyMuPDF import-version floor.
- [x] Inventory installed dependencies/attribution and attempt a clean install.
  Clean package retrieval and public-release license clearance remain blocked.
- [x] Save detailed evidence/results and a concise demonstration guide.

**Latest outcome:** 95 tests pass with no skips (plus 88 subtests), including a
clean-environment run. Approved live checks now pass for both providers, the actual
public SQuAD PDF-to-recovery flow, valid/404 URLs, and localhost app health. Root
URL equivalence was fixed after the first real-paper run exposed it. Browser visual
acceptance and public-release licensing remain unresolved. See docs/READINESS.md,
docs/DEMO.md, and THIRD_PARTY_NOTICES.md. This is a completed review with unresolved
browser/release gates, not a declaration that dataset bytes or public deployment
have been validated. No major new product feature was started.

## Current extension — Streamlit workflow and PDF links

- [x] Add bounded, in-memory PDF extraction in `relink/extraction.py`: text and
  annotation URLs, deduplication, page/context evidence, explicit invalid/encrypted
  or scanned-PDF limitations. No OCR, uploads persisted to disk, or PDF fetching.
- [x] Add a small report/workflow adapter that calls existing current-URL checks
  and discovery/ranking; include input context and UTC time in JSON exports.
- [x] Build `app.py` with Recover URL / Analyze PDF modes, link selection,
  explicit Recover action, genuine activity indicators, errors, ranked results,
  provenance links, verification labels, and export. Keep rendering and session
  state in `relink/ui.py`; no provider/ranking logic belongs in the UI.
- [x] Add mocked engine-flow tests and Streamlit AppTest tests for both modes,
  PDF errors, changed-input state, reruns, unsafe remote content/links, and export.
- [x] Run the complete suite and verify URL/PDF widgets through the existing
  engine in Streamlit AppTest; record separate unmocked runtime checks.
- [ ] Launch a browser-accessible server from an unrestricted host terminal and
  review visual appearance. Agent launch is blocked by socket permissions.

**Design:** Research workspace with a restrained teal/ink palette, warm neutral
background, readable system typography, generous spacing, native accessible
controls, bordered candidate cards, and clear labels. Show no sample results,
invented counts, percentage progress, or operational-looking placeholders.

**Acceptance:** Both modes run existing engine modules on explicit action. PDF
uploads yield selectable real links or honest limitations. Untrusted content is
plain text/JSON/table cells; clickable destinations must pass URL validation.
Unrelated reruns never repeat a search and changed inputs never retain stale
results. A completed report can be downloaded as JSON without PDF bytes.

**Validation status:** Dependencies installed by the user. Pytest now reports
87 passed, no skips, plus 85 passing subtests. Real PDF parsing and both native
widget-to-engine flows pass with mocked external HTTP/DNS. Separate unmocked
runtime attempts render DNS failures correctly and expose JSON export in both
modes; see `docs/ui-runtime-check.json`. Compilation, pip check, and whitespace
checks pass. Agent server startup fails with PermissionError opening a listening
socket; host launch and visual browser review remain pending.

## Current extension — DataCite discovery

- [x] Introduce `SearchQuery`, shared `Candidate`, provenance, provider search
  results, ranking explanations, and independent content-hash evidence models.
  Preserve existing Archive URL recovery output and CLI compatibility.
- [x] Implement public DataCite requests in `relink/providers/datacite.py` using
  the existing public-only client. Escape user query text, filter datasets, bound
  page count/results, preserve raw metadata, and retain partial results on errors.
- [x] Implement conservative DOI/URL deduplication in `relink/candidates.py`;
  preserve source provenance and keep distinct DOI versions separate.
- [x] Implement deterministic ranking in `relink/ranking.py` for titles, authors,
  institutions, years, filenames, URLs/DOIs, and descriptions. Return structured
  point contributions and conflicts; never label points as probabilities.
- [x] Add discovery orchestration and an Archive adapter using the shared model.
  Support verified_exact_match only with independent matching SHA-256 evidence;
  normal metadata search can produce likely_match, different_version, or
  unverified_candidate. Use not_found only for successful empty searches.
- [x] Add mocked tests first, run the complete suite, attempt a live DataCite
  query, and update STATUS.md with actual results and limitations.

**Acceptance:** Each supported search field can be used alone or combined. Both
providers return shared candidates. Duplicate identities retain every source;
distinct versions remain distinguishable. Failures are distinct from no matches.
Verification does not follow from DOI, title, URL, or score agreement alone.

**Historical outcome:** This milestone initially had 57 passing unittest cases
while pytest was unavailable. The final review now has 92 passing pytest tests.
The live public DataCite attempt still fails at DNS; successful live integration
remains unverified. See STATUS.md and docs/readiness/live-checks.json.

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

**Historical outcome:** The initial URL slice had 26 passing offline unittest
cases. These are included in the final 92-test pytest suite. Successful live
service access remains blocked by networking; see STATUS.md.

## Scope and module map

Accept a missing HTTP(S) URL or PDF; extract research links and nearby context;
search Internet Archive and DataCite; rank and explain candidates; show evidence
and verification status in Streamlit; evaluate on real broken links.

| Path | Responsibility |
| --- | --- |
| `app.py` | Thin Streamlit entry point |
| `relink/ui.py` | Native controls, session state, safe result rendering |
| `relink/workflow.py` | Existing-engine adapter and JSON report export |
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

- [x] Define shared types in `relink/models.py` before provider implementation.
  Candidates carry source, original URL, candidate URL, metadata, retrieval
  timestamp, evidence, and verification status. Provider outcomes distinguish
  success, empty results, and failure.
- [x] Implement URL validation and PDF extraction in `relink/extraction.py`.
  Extract text URLs and hyperlink annotations, deduplicate, and retain page
  numbers and nearby text. Preserve original URLs alongside normalized values.
- [x] Add `tests/test_extraction.py` with generated local PDF fixtures for
  annotations, wrapped/punctuated links, duplicates, malformed/encrypted PDFs,
  and PDFs without extractable text. Shared-model behavior is covered in the
  existing discovery and workflow tests rather than a redundant models-only file.

**Acceptance:** A URL or text-readable PDF yields structured context, or a clear
input limitation. Scanned PDFs do not silently appear successfully extracted.
Offline tests pass: `.venv/bin/python -m pytest tests/test_extraction.py tests/test_discovery.py tests/test_workflow.py`.

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

- [x] Implement `relink/providers/datacite.py` using URL and available paper
  context; preserve DOI, titles, creators, publisher, dates, and related IDs.
- [x] Implement `relink/recovery.py` against a common provider interface; a
  provider failure must not discard another provider's usable results.
- [x] Add `tests/test_datacite.py` and `tests/test_discovery.py` for sparse metadata,
  empty results, pagination limits, rate limits, timeouts, and partial failures.

**Acceptance:** Both providers return compatible candidates and distinct error
states. DataCite metadata alone never establishes file availability. Mocked
provider/orchestration tests pass without network access.

### M4 — Explainable ranking and verification

- [x] Implement `relink/ranking.py` with deterministic signals: exact URL/DOI,
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

- [x] Implement `app.py` with URL/PDF input, explicit search action, progress,
  ranked candidates, evidence, source links, and verification limitations.
- [x] Keep network calls in providers/services and avoid duplicate searches on
  unrelated UI reruns. Bound input size, result count, and request duration.
- [x] Add `tests/test_app.py` using mocked recovery calls and Streamlit's test
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
