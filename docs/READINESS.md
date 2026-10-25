# ReLink final readiness review

Follow-up: the owner selected AGPL-3.0-only; original-code LICENSE/NOTICE and
application source/license information are now implemented. The working suite
now passes 273 tests plus 192 subtests, including compact three-tab navigation, request-free input presets, combined dataset AI, bounded CSV/TSV samples, generation timeouts and multi-source paper ranking,
cached pagination, private history isolation and core Gemini identification,
persistent local history, two-tab abstract search and selected
paper dataset lookup. New evidence: [paper-feature-pytest.log](readiness/paper-feature-pytest.log)
and [PAPERS.md](PAPERS.md). Live OpenAlex/PDF extraction passed; related DataCite
records were empty and follow-up Archive was rate-limited. The earlier 95-test logs and clean install
below remain historical evidence. Real additional examples and limitations are
recorded in [evaluation.md](evaluation.md). Public source is now published at
[crqzyexprees/relink](https://github.com/crqzyexprees/relink), with anonymous source
access checked. Deployed-version source configuration and release checks remain pending.

## Compact navigation — 2026-10-25

Fresh full suite: **273 tests/192 subtests pass**, no failures/skips;
[output](readiness/navigation-pytest.log). Native AppTests verify legal content in
its own third tab, public input presets without requests, explicit Find and input
persistence across workspace reruns. The big hero/above-fold license block were
removed; source links remain accessible in the top navigation. Independent review
found no important issues. Compilation/whitespace checks pass. No backend/provider
change or new live result is claimed. Physical browser alignment remains unverified
because no browser execution tool is exposed in this session.

## Combined dataset AI and space workspace — 2026-10-25

Fresh full suite: **269 tests, 192 subtests pass**, no failures/skips;
[output](readiness/dataset-space-pytest.log). No dependencies added. Details:
[DATASET_AI.md](DATASET_AI.md). Compileall, pip check and whitespace checks pass.

| Check | Result | Evidence / limitation |
| --- | --- | --- |
| Bounded CSV/TSV sampler and safe transport | PASS, mocked | `test_dataset_preview.py`: ignored ranges, valid/invalid206,64KiB streaming cap, complete logical rows, UTF-8/cell/column bounds, redirects, errors/timeouts. |
| Dataset metadata plus sample AI assessment | PASS, live | [Exact checks](readiness/dataset-ai-exact-live.json): real three-row public CSV input and separate actual Iris DOI discovery; no verified bytes claimed. |
| Broad topic results | LIMITED, live | [Initial broad query](readiness/dataset-ai-live.json) returned30 real records but weak leads. Explicit relevance sorting added; no global-best/exhaustive claim. |
| Combined evidence, conflicts and fallback | PASS, mocked | Initial URL/DOI/hash scores/statuses survive PDF merging; actual named-version warnings retained; invalid IDs/references/quotas/timeouts preserve independent results. |
| Topic/URL/PDF/paper UI, cache and snapshots | PASS, mocked | Native AppTests, ten-at-a-time request-free pagination, source processing disclosure, JSON/sample round trips and existing history-isolation suite. |
| Original space theme | IMPLEMENTED | Static CSS stars/planet/orbits, navy/amber/cyan palette, contrast/reduced-motion/responsive checks; no remote assets. |
| Updated visual/hosted acceptance | BLOCKED | No browser executor exposed. Existing hosted paper search confirmed by owner; new theme/dataset UI still needs actual browser review. |

Read-only review found evidence loss during combining and missing paper-tab sample
disclosure. Both were reproduced by failing tests, fixed and followed by the full
suite. Additional real version-warning and complete PDF hash-handoff regressions
pass. Earlier provider/AI tests and live reports remain separate dated evidence.

## Generation timeout fix — 2026-10-25

Full mocked suite: **209 tests, 181 subtests pass**; [output](readiness/generation-timeout-pytest.log).
Gemini POSTs now get 60s read inactivity/90s cooperative elapsed; ordinary
network defaults and DNS/connect/write/pool bounds remain. Simulated slow
generations, elapsed expiry, default restoration, invalid settings and one-call
timeout fallback pass. Independent review found no important defects.

Both [before](readiness/paper-ranking-timeout-before.json) and
[after](readiness/paper-ranking-timeout-after.json) fresh real generations accepted
26 public abstracts; observed read allowances changed from 10s to 60s, with
connect/write/pool still 10s. Both finished in under four seconds. The exact hosted
delay is **unverified**, rather than reproduced by those fast live calls. The
elapsed budget remains cooperative; strict header cancellation is still open.

## Ranking validation fix — 2026-10-25

- Owner reported hosted `invalid response`; screenshot usage was below the shown
  free-tier quotas. Exact hosted query/response was not supplied. The generic
  warning previously combined several validation failures; earlier actual output
  included overlong source quotes.
- Model now selects numbered source passages instead of generating quotes. Only
  actual own-paper passages can populate evidence. Complete paper-ID ordering,
  bounds, safe rendering and keyword fallback remain; failure details now state
  a safe specific reason. No retries, billing upgrades or extra requests on Load more.
- Fresh full suite: **203 tests, 169 subtests pass**, no failures/skips;
  [output](readiness/paper-ranking-grounding-pytest.log). New tests cover complete
  referenced output, wrong references/types, free-form quote rejection, cross-paper
  binding, Unicode/whitespace/long tokens, no usable text and diagnostics.
- Actual [first-batch check](readiness/paper-ranking-grounding-live.json) accepted
  26 Gemini-ranked papers; [next batch](readiness/paper-ranking-grounding-live-next-batch.json)
  accepted 25 unseen papers with no previous identity overlap. Both source APIs
  returned real responses; stored reports never feed production results.
- Updated hosted browser acceptance remains unverified. Earlier failed/successful
  quote-generation reports below remain historical evidence.

## Paper-ranking upgrade — 2026-10-25

Fresh full suite: **191 passed, 159 subtests passed**, no failures/skips;
[output](readiness/paper-ranking-pytest.log). No new dependency was added.

| Check | Result | Supporting evidence / limit |
| --- | --- | --- |
| Up to 30 unique records, provenance and abstract-only ranking | PASS | Mocked `tests/test_paper_ranking.py`; model never supplies paper URLs/metadata. |
| Both public paper sources | PASS, live | [First batch](readiness/paper-ranking-live.json): OpenAlex/arXiv each returned 15 records. |
| First-batch Gemini output acceptance | FAIL, live | Latest output was rejected; 24 real keyword matches remained. No replacement AI ranking or retry. |
| Explicit next-batch Gemini ranking | PASS, live | [Next batch](readiness/paper-ranking-live-next-batch.json): 25 unseen papers, checked quotes, no previous identity repeated. |
| Cached Load more (10 → 20 → 30) | PASS, mocked UI | Native AppTest confirms no new HTTP/model calls and selected-paper dataset lookup still works. |
| Errors, quota, timeout, missing key, empty results | PASS, mocked | Explicit fallback/partial statuses; no fabricated candidates. |
| Dedup aliases and skipped-record pagination | PASS, mocked | Review regressions first failed, then passed; retained source URLs and raw page fullness. |
| Saved evidence, old snapshots, private identity boundaries | PASS, mocked | Full history/UI/isolation regressions pass; actual OIDC remains separate acceptance. |
| Hosted-browser upgrade / physical clicks | BLOCKED | Browser execution tool unavailable; AppTest and live modules do not establish hosted acceptance. |

Gemini output remains variable and can fail strict validation. All evidence
reports are historical observations, never app fallbacks. Topic and bounded
public abstract excerpts go to Google only on explicit search; no full PDFs are
downloaded for relevance ranking. Source rights and multi-process rate-limit
limits are documented in PAPERS.md and THIRD_PARTY_NOTICES.md.

Latest code/UI review: [REVIEW.md](REVIEW.md), [suite output](readiness/review-pytest.log),
and [live follow-up](readiness/review-live.json). TLS-origin isolation, safe escaped
path identity, ranking false positives, and persistent errors were fixed. Strict
HTTP header deadlines and native PDF isolation remain open; the new elapsed-budget
checks do not establish a hard wall-clock bound.

Private history: [AUTH.md](AUTH.md),
[latest suite output](readiness/history-isolation-pytest.log),
[JUnit](readiness/history-isolation-pytest.xml). Two accounts, guests, expiry,
stale dialogs and changed identity during remote work pass mocked acceptance.
Private browser-local exports avoid unauthenticated media URLs. Actual OAuth
redirects/cookies and browser Blob downloads remain BLOCKED pending provider
configuration/manual browser acceptance. No live login success is claimed.

Historical shared-store verification: [HISTORY.md](HISTORY.md),
[suite output](readiness/history-pytest.log), [JUnit](readiness/history-pytest.xml).
Separate-process disk persistence and fresh-session request-free viewing passed.
That original shared store is now accessible only in explicit single-operator
local mode; default private accounts never inherit it. No PDF files are saved.

Reviewed 2026-10-24; updated after approved execution outside the sandbox.
**Automated, live-provider, real-paper, and clean-install checks pass.** Visual
browser/manual acceptance and public-release licensing remain outstanding.
Earlier restricted attempts remain recorded separately rather than erased.

PASS means the stated check ran and met its expectation. BLOCKED means the
expectation could not be assessed; it is not a successful empty search. Mocked
and live checks are separate below. No fallback candidates or fake successes were added.

## Results

| Hosted check at relink.streamlit.app | Result | Supporting output and scope |
| --- | --- | --- |
| Public HTTPS address and Cloud cookie redirects | PASS | [hosted-deployment-http.json](readiness/hosted-deployment-http.json): cookie-aware root request returns HTTP 200 at the owner-supplied hostname. |
| Underlying Python health | BLOCKED | /_stcore/health returns the same Cloud HTML wrapper as root, not plain ok. HTTP 200 here does not establish engine health. |
| Hosted URL/PDF/Gemini/source/history/export flows | BLOCKED | No browser-control execution tool exposed; owner visible-browser state requested. Previous local mocked/live-provider tests do not establish hosted acceptance. |

| Private-history check | Result | Supporting output and scope |
| --- | --- | --- |
| Current complete suite | PASS | [history-isolation-pytest.log](readiness/history-isolation-pytest.log): `173 passed, 142 subtests passed in 9.45s`; no skips/failures. |
| Per-account list/save/view/rerun/export/delete/clear | PASS | `tests/test_history_isolation.py`: two identities, stable same-account fresh session, different issuers, guest/expiry/invalid denial and legacy-file isolation. Mocked identity, real storage/UI. |
| Changed identity during success/failure; stale dialog fragment | PASS after fixes | Regressions observed failing before fixes; normal requests and reruns discard prior-account results, fragment denial resets the full app. |
| Private export transport/content safety | PASS, contract scope | Encoded actual current-account payload tested; no global media download registered. Malicious markup stays inert bytes. Physical browser file download still unverified. |
| Official auth dependency install and consistency | PASS | [auth-install.log](readiness/auth-install.log), [incremental license inventory](readiness/auth-dependencies.json), pip check passes. |
| Actual provider login/logout/cookie and browser download | BLOCKED | OAuth application/client credentials and manual browser acceptance are not configured. No live login test was performed. |

Latest Gemini milestone evidence is separate from the historical 95-test review
below. See [GEMINI.md](GEMINI.md) for privacy, bounds, and interpretation.

| Added check | Result | Supporting output and scope |
| --- | --- | --- |
| Gemini milestone suite | PASS | [gemini-pytest.log](readiness/gemini-pytest.log): `156 passed, 125 subtests passed in 7.00s`; mocked external HTTP/DNS, no real key. |
| Core identification in both UI flows | PASS | `tests/test_gemini_app.py`: paper lookup and link-free upload run actual modules over mocked services; no calls on upload/rerun/saved views. |
| Grounding, errors, credential handling | PASS | `tests/test_gemini.py`: quotes/names/pages/versions, partial and empty output, malformed JSON, auth/429/timeouts, HTTPS-only POST, redirect/header isolation, bounded requests and per-name failure isolation. |
| Live Gemini + actual public paper + DataCite | PASS, partial identification | [live-gemini.json](readiness/live-gemini.json): seven supported mentions, five locally extracted replacement quotes explicitly flagged, five real DataCite records for each of three names. No file/version identity verified. |
| Fresh browser walkthrough/new clean install | BLOCKED / not rerun | Browser tools unavailable. Earlier clean install still covers 95 tests; no dependencies were added for Gemini. |

| Important feature/check | Result | Supporting output and scope |
| --- | --- | --- |
| Complete pytest suite | PASS | [pytest.log](readiness/pytest.log): `95 passed, 88 subtests passed in 4.07s`; no skips/failures. [JUnit](readiness/pytest.xml) includes 183 cases with subtests. |
| Streamlit URL input → engine → ranked results | PASS | `EngineUIIntegrationTests::test_url_widgets_run_existing_engine_and_export_without_repeating_requests`; real widgets/modules, mocked external HTTP/DNS. |
| Native PDF upload → extraction → link selection → recovery | PASS | `EngineUIIntegrationTests::test_native_pdf_upload_select_recover_and_remove_clears_report`; actual generated PDF bytes and PyMuPDF, mocked HTTP/DNS. |
| Actual public research PDF → live recovery | PASS | [host-live-checks.json](readiness/host-live-checks.json): actual SQuAD PDF downloaded, 10 pages/3 extracted URLs, dataset link selected, genuine Archive candidate returned as likely_match/archive_metadata_only. No fixture substituted; dataset bytes remain unverified. |
| Internet Archive response parsing | PASS | `RecoveryTests` cover a reported capture, empty/unavailable captures, malformed captures, HTTP errors, 429, and timeouts. Responses are mocked. |
| Internet Archive live integration | PASS | Approved live request returned HTTP 200 and a reported capture dated 20250407122419. Original restricted DNS failure remains in [live-checks.json](readiness/live-checks.json); successful evidence is [host-live-checks.json](readiness/host-live-checks.json). |
| DataCite query/parsing/pagination | PASS | `DataCiteTests`: each input alone/combined, sparse data, validation, pagination limits, partial responses, and failures; mocked responses. |
| DataCite live integration | PASS | HTTP 200 with actual Iris DOI `10.24432/c56c76` and returned repository URL `https://archive.ics.uci.edu/dataset/53`. [Approved live evidence](readiness/host-live-checks.json). |
| DOI resolver URL in the main UI | PASS after fix | `test_doi_url_redirects_and_repository_identity_search_work_together`; native UI, DOI redirect, DataCite identity query, likely-match status; mocked external responses. |
| Valid URLs, 404, 403, 429 and other HTTP statuses | PASS | `RecoveryTests::test_current_http_statuses_stay_distinct`; mocked 2xx/404/403/429/410/500. |
| Live valid/broken URL probes | PASS | Approved requests observed working https://example.org/ and an actual 404 from https://httpbin.org/status/404. [Live evidence](readiness/host-live-checks.json). |
| Redirects, loops and unsafe destinations | PASS | `RecoveryTests` verify safe redirect history, limits, localhost/private targets, downgrade rejection, and API redirects. |
| Bad, empty, oversized and encrypted PDFs | PASS | `PDFTests` and `PDFAppTests`; actual invalid/generated/encrypted inputs, visible errors, disabled recovery. |
| No-text/scanned and link-free PDFs | PASS | Real local parser tests return explicit limitations/empty links; no OCR or invented links. |
| Rate limits | PASS | Archive/DataCite mocked 429 responses expose Retry-After and are not automatically retried; later-page 429 preserves partial results. Actual provider throttling was not forced. |
| Timeouts and DNS failure | PASS | Mocked connect/read/DNS timeouts, distinct DNS/connection errors, and continued independent provider lookup. |
| Empty results versus service failure | PASS | `test_missing_archive_is_not_found`, `test_empty_results_and_service_failure_are_distinct`, and UI partial/empty/error cases. |
| Deduplication, ranking and version status | PASS | `DiscoveryTests`; original source/DOI provenance retained, deterministic point explanations, distinct versions, independent-hash gating. Scores are not probabilities. |
| JSON export and repeat-request prevention | PASS | UI export payload tested; native download widget and unrelated reruns do not repeat HTTP requests. Physical browser download remains unverified. |
| No sample candidates displayed as live results | PASS | Source review found fixtures confined to tests; `test_initial_view_has_two_modes_and_no_fake_results` and `test_dns_failures_do_not_display_sample_candidates` show no candidate cards on idle/failure. Live attempts also returned no invented candidates. |
| Safe remote-content rendering | PASS, contract scope | UI tests check malicious HTML/Markdown stays in plain-text elements and unsafe links are not clickable. Public-DNS pinning and redirect tests pass. This is not a comprehensive browser/security audit. |
| Working-environment dependency consistency | PASS | [environment.log](readiness/environment.log): Python 3.12.15, Streamlit 1.66.1, HTTPX 0.28.1, PyMuPDF 1.28.2, pytest 9.1.1; `No broken requirements found.` |
| README clean environment creation | PASS | [clean-environment.log](readiness/clean-environment.log): a new isolated Python 3.12 environment initially had none of the four application/test packages. |
| README fresh dependency installation and clean test run | PASS | Approved pip installation into the isolated /tmp environment succeeded from the package index. [clean-pytest.log](readiness/clean-pytest.log): 95 passed plus 88 subtests; [environment and pip check](readiness/clean-environment-final.log). No packages copied from the working environment. |
| Dependency and attribution inspection | PASS, review scope | [42-package inventory](readiness/dependencies.json) and [third-party notices](../THIRD_PARTY_NOTICES.md); this is not compliance/vulnerability certification. |
| Public distribution/license clearance | BLOCKED pending release checks | AGPL-3.0-only source, LICENSE/NOTICE and app source/license entry exist; GitHub publication/anonymous access pass. Configure the deployed-version source link and confirm contributor/dependency obligations; see [LICENSING.md](LICENSING.md). |
| Existing Streamlit server health | PASS | Approved HTTP probe returned 200 with body `ok` on localhost:8501. The existing host server was used; the earlier sandbox startup denial remains in [server-start.log](readiness/server-start.log). |
| Visual browser review and real browser export | BLOCKED | HTTP health now works, but browser automation is not exposed in this session. AppTest acceptance is not visual/browser acceptance. |

## Bugs found and fixed

1. **DOI resolver URLs could miss their own repository record.** The form passed a
   DOI URL only as a website address. Combining URL and DOI constraints could also
   require a catalog's landing-page URL to equal the DOI resolver URL. Two tests
   failed before the fix. SearchQuery now derives the DOI from a validated resolver
   URL, and DataCite omits that redundant URL constraint. Original URL and redirect
   evidence remain in reports. A native UI-to-engine regression test now passes.
2. **The declared PDF dependency floor was too low.** Code imports `pymupdf`, which
   was introduced in [PyMuPDF 1.24.3](https://pymupdf.readthedocs.io/en/latest/changes.html).
   requirements.txt now declares `PyMuPDF>=1.24.3,<2`. The installed 1.28.2 works;
   installation/execution on the minimum version itself was not tested.
3. **Sparse DataCite requests omitted dataset rights metadata.** Added `rightsList`
   to requested fields so original-source records preserve the returned rights for
   attribution review. The new request/provenance test failed before the fix and
   passes afterward. Rights metadata is not treated as identity or reuse proof.

4. **A real-paper run exposed root-URL equivalence rejection.** The paper's dataset
   URL lacked a final slash, while Archive reported the equivalent root address
   with `/`. The initial live response was rejected as invalid_response; the
   diagnostic initially labeled the whole paper check BLOCKED. The original
   evidence is preserved in [host-live-before-root-fix.json](readiness/host-live-before-root-fix.json).
   URL identity now canonicalizes empty root paths to `/`, while preserving
   non-root trailing slashes, escaped separators, and query distinctions. Two
   failing regression tests were made to pass, with a third guarding non-root
   mismatches. The real paper now produces a genuine archive metadata candidate.
   The diagnostic also labels future invalid-response failures FAIL, not BLOCKED.

The baseline was 87 passing tests; the final suite is 95 passing tests. Changes
are limited to integration fixes, regression coverage, review evidence, and a live
diagnostic script. No frontend fallback, additional provider, or major feature was added.

## Interpretation and release gates

Both mocked and actual service-backed paths now work. At 2026-10-24T22:42:13 UTC,
approved execution downloaded [arXiv:1606.05250](https://arxiv.org/abs/1606.05250),
parsed the actual 10-page PDF, extracted three web URLs, and recovered an Archive
lead for its dataset URL. It is a reported webpage capture, not verified dataset
bytes or independently tested replay accessibility. All six live diagnostic
checks passed. Visual browser acceptance remains outstanding.

The license review is material: attribution alone does not satisfy PyMuPDF's
AGPL/commercial choice. The owner subsequently authorized the AGPL route; source
is published; deployed-version configuration and applicable release checks remain pending. Upstream also
lists native text-extraction hangs affecting the installed major line; existing
input limits do not preempt a stuck native parser. See THIRD_PARTY_NOTICES.md.

## Reproduce the live checks

From the normal host terminal with the app running:

```bash
.venv/bin/python -m scripts.check_readiness --output docs/readiness/host-live-checks.json
```

Use `--paper /path/to/public-paper.pdf` for an already downloaded actual paper.
The script records real responses and keeps provider failures distinct from
not-found. It does not promise a recovered dataset. Clean-install commands and a
short presentation walkthrough are in [DEMO.md](DEMO.md).
