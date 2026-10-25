# ReLink

Paper-aware dataset recovery for HackPSU 2026. The first feature checks a public
URL and searches Internet Archive for a reported capture. Dataset discovery now
searches DataCite, deduplicates candidates, and ranks them with structured evidence.
PDF link extraction and the two-mode Streamlit UI pass runtime tests with mocked
external services. Browser server launch requires a host terminal. See [PLAN.md](PLAN.md),
[STATUS.md](STATUS.md), and [AGENTS.md](AGENTS.md).

The UI now has **Find datasets** and **Find papers** tabs. Find papers accepts a
topic/description, retrieves OpenAlex records, and ranks actual abstract keyword
matches. Select a paper to search related dataset metadata and extract research
links from an advertised public PDF, then run the existing recovery engine on a
selected link. **Gemini is built into paper/PDF dataset lookup:** it identifies
dataset names from the text, ReLink checks supporting excerpts locally, and
DataCite supplies actual ranked repository records. It also works with readable
PDFs that have no dataset links. A Gemini key is needed for this identification;
URL recovery and abstract keyword search remain available without it. No new
dependency was added. See [Gemini configuration and evidence](docs/GEMINI.md).
See [paper search and limitations](docs/PAPERS.md). Keyword scores are not semantic
similarity, research-quality ratings, or proof that a dataset was used in a paper.

**Search history is private per signed-in account and survives browser/app restarts.**
The sidebar reopens dated snapshots without requests, reruns searches explicitly,
and exports/deletes/clears only that account's records. Configure native Streamlit
OIDC with Google or Auth0 using [the login setup guide](docs/AUTH.md). Guests can
search without disk history. Missing/expired identity never opens shared history.
Files use `.relink/history-users/<opaque namespace>.json`, with up to 50 entries
per account and no PDF files. Legacy `.relink/history.json` is untouched and
requires explicit single-operator local mode; see [storage and limits](docs/HISTORY.md).

Latest verification: **173 tests and 142 subtests pass**; the earlier clean-environment run passed
95 tests. Approved live
checks pass for both providers, actual SQuAD PDF recovery, and app health.
See the [pass/fail/blocked results](docs/READINESS.md),
[demonstration guide](docs/DEMO.md), and [dependency/attribution review](THIRD_PARTY_NOTICES.md).
For real inputs with dated live outcomes, see [evaluation examples](docs/evaluation.md).
Public source is available at [crqzyexprees/relink](https://github.com/crqzyexprees/relink).
Visual browser acceptance, configuring the deployed-version source link and the
remaining release checks stay open. Archive metadata does not verify dataset bytes.

Hosting recommendation and demo configuration: [DEPLOYMENT.md](docs/DEPLOYMENT.md).
The proposed 30-paper Gemini reranking/Load more extension is documented in
[PAPER_SEARCH_NEXT.md](docs/PAPER_SEARCH_NEXT.md); current paper ranking still
uses abstract keywords.

## Open-source license

Copyright (C) 2026 ReLink contributors. ReLink's original application code is
licensed under **AGPL-3.0-only**; see [LICENSE](LICENSE) and [NOTICE](NOTICE).
You may redistribute and modify it under those terms. It is provided without
any warranty, including merchantability or fitness for a particular purpose.
Dependencies keep their own licenses; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
Uploaded papers and linked datasets retain their separate rights.

Before public deployment, publish the corresponding source for the exact deployed
release and set `RELINK_SOURCE_URL` to its accessible public release/tag URL.
The app displays that link alongside its license notice. For example, after
setting your actual URL in the shell:

```bash
export RELINK_SOURCE_URL='https://github.com/YOUR-ACCOUNT/YOUR-REPOSITORY/tree/YOUR-RELEASE-TAG'
.venv/bin/python -m streamlit run app.py
```

Replace all uppercase placeholders. `.env.example` documents the variable; it is
not loaded automatically. Confirm team/contributor rights, retain dependency
notices, and review source obligations for the actual release artifact, especially
if distributing a bundled environment/container. See [the release checklist](docs/LICENSING.md).

## Setup

Python 3.12 is the initial verification target.

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
```

Requirements include Streamlit's official `auth` extra. To activate private
history, register an OIDC web application and add its `[auth]` configuration to
the ignored secrets file, preserving the Gemini values at the top level. See
[AUTH.md](docs/AUTH.md) and [the blank example](.streamlit/secrets.example.toml).
The Gemini key cannot authenticate users; OAuth client credentials are separate.
Until configured, ordinary searches work and disk history stays unavailable.

For core paper/PDF identification, add your Google AI Studio key to the ignored
`.streamlit/secrets.toml` (top-level TOML):

```toml
GEMINI_API_KEY = "YOUR_KEY"
GEMINI_MODEL = "gemini-3.5-flash-lite"
```

Environment variables with these names take precedence. Never commit the key.
Use the free-tier project as intended; the app does not enable billing or control
Google's project billing/quota settings. Before Find, the UI discloses that bounded
text excerpts go to Google. Use public, nonconfidential papers. A missing key,
rate limit, or model error is shown explicitly and preserves independent results.

The user installed requirements from the host terminal. The verified environment
has Streamlit 1.66.1, PyMuPDF 1.28.2, and pytest 9.1.1; pip check passes. The
Streamlit minimum is 1.66 for native upload/download AppTest APIs and current
layout sizing. Requirements use version ranges, not a lockfile. This agent's
sandbox restricts networking by default; approved commands can now run outside it.

## CLI demo

```bash
.venv/bin/python -m scripts.recover_url 'https://www.psu.edu/'
```

JSON output contains `original_url`, `current`, and `archive`. Current status
separates `working`, `not_found` (404), `forbidden` (403), `rate_limited` (429),
`dns_failure`, `timeout`, `blocked`, `redirect_error`, `http_error`, and
`network_error`. Final URL, redirect history, and HTTP status are included.

The [Internet Archive availability API](https://archive.org/help/wayback_api.php)
adapter can return a `found` candidate with original URL, archived URL, capture
timestamp, source, retrieval time, and evidence. Other outcomes are `not_found`,
`rate_limited`, `timeout`, `dns_failure`, `blocked`, `error`, or `invalid_response`.
An API failure never becomes a not-found result.

Every candidate is `archive_metadata_only`: replay accessibility and downloadable
dataset preservation have not been checked. Replay host, embedded original URL,
and capture timestamp must agree before a candidate is accepted. The lookup uses
the original URL even if it currently redirects. Working URLs also get a lookup.

Exit codes: `0` for a completed archive search (`found` or `not_found`), `1` for a
blocked/failed lookup, and `2` for invalid or unsafe input. Exit `0` does not claim
that a dataset was recovered.

## Request policy

- Public HTTP/HTTPS addresses on standard ports only. Credentials, internal
  names, non-public IPs, and mixed public/private DNS answers are blocked.
- Connections use a vetted IP with the original Host header and TLS server name,
  preventing a second hostname resolution from rebinding to an internal address.
  Environment proxies are disabled.
- Every redirect gets the same validation. HTTPS downgrades, loops, and missing
  redirect locations are errors. Maximum five redirects per fetch.
- DNS waiting and each HTTP connect/read/write/pool operation have ten-second
  inactivity limits. A 30-second fetch budget is checked between redirects and
  body chunks, and remaining time reduces subsequent operation limits. It is
  cooperative: slowly delivered headers inside HTTPX can still exceed it; this
  is not a strict wall-clock deadline for a request or the complete workflow.
- IP-pinned transport connections are not reused, ensuring each destination
  hostname receives its own TLS handshake/verification even when IPs are shared.
- Current checks use streamed GET requests and close without reading the body.
  API bodies are limited to 1 MiB. Compressed API bodies are rejected.
- No automatic retries. Rate limits expose `Retry-After` for the caller to honor
  before another attempt. Each CLI run makes one recovery attempt.

## Dataset discovery

```bash
.venv/bin/python -m scripts.discover_datasets --title 'forest soil' --author 'Ada Lovelace' --year 2020
.venv/bin/python -m scripts.discover_datasets --description 'temperate forest carbon observations'
.venv/bin/python -m scripts.discover_datasets --institution 'Penn State University'
```

These are example search inputs, not claims that matching resources exist.
Optional `--doi`, `--url`, `--filename` (repeatable), and `--version` provide more
context. Each search field can be used alone. An original `--url` also invokes
Internet Archive; the original URL recovery CLI is still available.

Python callers can use `SearchQuery` and `discover_datasets` from `relink.models`
and `relink.recovery`. Future providers implement `DiscoveryProvider.discover`
and return `SearchResult` containing shared `Candidate` instances. The Archive
adapter supports both this interface and its original `search(url)` interface.

DataCite requests use the [public dataset API](https://support.datacite.org/docs/api-get-lists)
and documented [metadata query fields](https://support.datacite.org/docs/queries).
Supplied fields are combined with AND; description words use OR within that
field. Title and author words use prefixes, so partial names and reversed author
name order are supported. Institution searches cover affiliations, organizational
creators, and publishers. URL/DOI searches include related identifiers; a related
record is evidence to assess, not an exact identity assertion.

The adapter defaults to 20 candidates, 20 records per page, and at most two pages.
Configurable hard caps are 100 candidates, 25 records per page, and five pages.
It rebuilds pagination requests against DataCite rather than following returned
next-page URLs. Later failures retain earlier candidates as partial results.
Malformed/non-dataset records are reported in warnings. Empty successful searches
are distinct from service failures, malformed responses, and incomplete searches.

Retrieval prefixes are not identity evidence: local ranking gives whole-word
agreement more weight than partial title prefixes. Author and other metadata
signals use whole words, reducing false matches such as Iris/Irish and
Fisher/Fisheries. See [the review findings and remaining limits](docs/REVIEW.md).

Original returned DOI/URL and raw attributes (including creators, publisher,
dates, versions, and related identifiers) remain in `Candidate.provenance`.
Returned links are untrusted metadata and are not visited. Deduplication uses a
normalized DOI, or an identical normalized URL when both candidates lack a DOI.
Distinct DOIs and distinct archive captures remain separate; similar titles alone
are never deduplicated. Merged candidates retain every source and returned link.

## Ranking and match status

Every ranked result includes `score`, `status`, and an `explanation` list with
signal name, point contribution, reason, query values, and observed values.
Scores are raw heuristic points, never calibrated probabilities or percentages.

| Signal | Points |
| --- | --- |
| Title token overlap | 0–30 |
| Author token overlap | 0–20 |
| Institution/publisher overlap | 0–10 |
| Description/title overlap | 0–10 |
| Publication year | +10 match, −5 conflict, 0 missing |
| Exact filename | +10 |
| Returned resource or identity URL | +50 |
| DOI | +60 |
| Explicit different version | −20 |
| Independently supplied matching SHA-256 | +300, counted once |
| Independently supplied conflicting SHA-256 | −300 per observation |

Only requested signals contribute. Missing metadata is neutral. Relevance ties
sort by DOI, URL, and source. Filenames and metadata agreement are supporting
signals, not content proofs. The user's search URL is never counted as DataCite
evidence unless the returned record actually identifies it.

| Status | Meaning |
| --- | --- |
| `verified_exact_match` | Valid independent reference/candidate SHA-256 evidence agrees for this candidate URL |
| `likely_match` | DOI/identity URL agrees, or substantial title overlap has supporting author, institution, year, or filename evidence; no year/hash conflict |
| `different_version` | Explicit DOI version relationship, or conflicting version metadata for an otherwise identified dataset |
| `unverified_candidate` | Metadata is insufficient or conflicting |
| `not_found` | Search-level outcome when every applicable provider completed successfully without candidates |

`HashEvidence` is a trusted Python API input for a caller with an authoritative
reference hash and an independently computed hash of the same complete resource.
It records both sources and scopes evidence to a returned candidate URL. Both
must be valid SHA-256 values, with distinct nonempty provenance sources. This
feature does not download resources or compute/authenticate those hashes.
Providers never construct hash evidence from API metadata; ordinary discovery
therefore cannot produce a verified exact match. Contradictory hash observations
prevent verification. Provider-level `verification_status` describes the source
evidence (`metadata_only` or `archive_metadata_only`); ranked status is the match
assessment after any explicitly supplied independent checks.

The CLI returns 0 for completed found/not-found searches, 1 for partial/failed
searches, and 2 for invalid input. Provider details remain available in JSON even
when another provider fails.

## Tests and live checks

```bash
.venv/bin/python -m pytest -q
# Equivalent runner when pytest is unavailable:
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m compileall -q app.py relink scripts tests
```

The pytest-compatible unittest suite uses HTTPX MockTransport and mocked DNS.
Unexpected real DNS fails a test. Tests exercise the production validators,
transport, status checks, provider, orchestration, and CLI.

Live checks run separately. The attempt against `https://www.psu.edu/` failed at
DNS before either HTTP service was reached; see [the live record](docs/live-url-check.json).
That earlier attempt did not verify a capture. The later approved checks in
docs/readiness/host-live-checks.json report real capture metadata; dataset-byte
preservation remains unverified.

The earlier [live DataCite record](docs/live-datacite-check.json) attempted
`--title iris` without mocks. DNS failed before DataCite returned an HTTP response.
The discovery examples in automated tests are mocked fixtures. The later approved
live check independently returned actual Iris metadata and a repository URL.

## Git in this workspace

The repository metadata has been moved to the standard `.git` location on the
host. Normal Git commands now work:

```bash
git status
```

The completed work is committed in focused licensing, dataset-engine, paper/Gemini,
UI/history and documentation commits and pushed to the public
[GitHub repository](https://github.com/crqzyexprees/relink). Future changes should
remain scoped, tested commits in the same repository.

## Streamlit app

After installing requirements, run from the project root:

```bash
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

When the server starts successfully, open `http://127.0.0.1:8501`.
Run that command from your normal host terminal. Starting a server from this
agent's sandbox fails with PermissionError when creating the listening socket.
Browser appearance has not been visually verified in this session.

- **Recover URL:** enter a public HTTP(S) address and click Find. No description
  is required. Current access and both providers are checked once.
- **Analyze PDF:** upload a paper and click Find to identify dataset mentions and
  search real repository records. If links are extracted, select one for the
  existing URL/Archive recovery as well. No description or AI toggle is required.
- Inspect ranked candidate cards, source/DOI links, capture/retrieval timestamps,
  provenance, point contributions, and verification limitations.
- Optionally download the evidence report as JSON for sharing or auditing,
  including errors or partial results. This is not a dataset download. Reports
  contain input metadata and selected context, never the uploaded PDF bytes.

Extraction is local and in memory, with a 10 MiB upload limit, 100 pages, one
million extracted text characters, and 250 unique links. Text URLs and hyperlink
annotations are combined with page/context evidence. Line-wrapped links may be
joined heuristically and are explicitly flagged for review. Password-protected,
malformed, oversized, and scanned PDFs produce clear errors/limitations. Readable
link-free PDFs can use Gemini identification with the configured key; OCR is not
implemented. No PDF files or full page text are written from uploads. Short
supporting excerpts and result snapshots can be saved in local history.

Progress indicators correspond to actual extraction, current-URL checking, and
provider search work. There are no simulated percentages or demo results. Search
only runs on Find; reports persist across unrelated reruns and are cleared
when mode, URL, selected PDF link, document, or context changes.

Remote titles, URLs, context, errors, and evidence render as plain text or native
table/JSON values. Only constant application CSS uses HTML. Candidate/source links
must pass the existing syntactic public-URL policy before becoming clickable;
network requests use the engine's stricter DNS and redirect validation.

UI tests live in `tests/test_app.py`. Focused tests use mocked recovery; integration
tests drive native URL/upload/select/download widgets through real extraction,
current-status, discovery, ranking, and export modules. Only external HTTP/DNS are
mocked in those integration tests. Real PyMuPDF parsing uses generated local PDFs.
The suite currently passes all 173 tests plus 142 subtests, with no skips.

After installing dependencies, verify both flows with:

```bash
.venv/bin/python -m pytest -q
```

Then manually check a public URL and a text-readable PDF in the browser. Earlier
unmocked AppTest attempts of both modes are recorded in
[the runtime check](docs/ui-runtime-check.json): no render exceptions, DNS failures
surfaced correctly, and JSON export available. The PDF in that check is a generated
fixture. Later approved checks verified actual providers and the real SQuAD paper
flow; actual browser download and visual layout remain unverified. No dataset-byte
recovery has been claimed.

For the final live preflight, run `.venv/bin/python -m scripts.check_readiness`
from a network-enabled host. It writes observed results under `docs/readiness/`,
downloads the actual public SQuAD paper when available, and never substitutes
fixture candidates. Standard DOI resolver URLs pasted into Recover URL now also
populate the DOI identity query. The PyMuPDF floor is 1.24.3, matching its module name.
