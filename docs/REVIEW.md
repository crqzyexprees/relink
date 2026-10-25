# ReLink code, UI, and reliability review

Reviewed 2026-10-24 local time / 2026-10-25 UTC. Read current project rules,
plans/status, engine/provider/extraction modules, both Streamlit workspaces, and
tests. A separate read-only reviewer reproduced network/provider issues offline
and re-reviewed the fixes. Existing uncommitted user work was preserved.

## Findings and changes

| Priority | Finding | Outcome and supporting evidence |
| --- | --- | --- |
| P1 | IP-based connection pooling could reuse the first hostname's TLS connection for another hostname sharing its IP. | **Fixed.** Default keep-alive disabled. A real HTTPX/httpcore transport with an offline fake network demonstrates separate handshakes for both names; `NetworkLimitTests.test_same_ip_origins_each_receive_their_own_tls_handshake`. Extra TLS connections are a deliberate isolation tradeoff. |
| P2 | Inactivity limits alone let slowly delivered response bodies and redirect chains run for a long time. | **Partially mitigated.** Added a 30-second cooperative fetch budget, checked at redirects/body chunks, with shrinking per-I/O/default DNS limits. Fake-clock body/redirect regressions pass. Strict header-time cancellation remains open below. |
| P2 | Archive rejected safe path escape differences such as `~` versus `%7E`. | **Fixed.** Normalize safe unreserved path characters, preserve query bytes, encoded dots, reserved separators, and meaningful trailing slashes. Boundary regressions pass. A real CIFAR availability lookup now returns the reported capture. |
| P2 | Prefix scoring let Iris match Irish, and Fisher match Fisheries, as if identity evidence. | **Fixed.** Whole-word author/metadata signals and half-weight partial title prefixes. True Iris ranks above the unrelated marine record in a live DataCite query; the latter is unverified. Existing partial-title tests still pass. |
| P2 | The selected paper's own DOI could reappear as a dataset link through aliases/casing. | **Fixed.** Normalize DOI identity before link selection; keep unrelated dataset DOIs. Mocked regression covers `http://dx.doi.org/10.1234/PAPER`. |
| P2 | Deeply nested JSON could escape provider error handling and discard independent results. | **Fixed.** All three providers classify JSON RecursionError as invalid_response. Mocked 30 KB deeply nested bodies exercise every parser. |
| P2 | Input/action errors disappeared on an unrelated Streamlit rerun. | **Fixed.** Store errors in the relevant workflow state, preserve without rerunning failed requests, clear when relevant inputs change. URL, paper validation, and dataset lookup regressions pass. |
| P3 | Paper-search explanations and very long abstracts pushed useful actions down the page. | **Improved.** Short introductory copy, expandable matching details, and a 1,200-character abstract preview with full abstract disclosure. Keep source, matched terms, and score visible. |
| P3 | Token sets were repeatedly rebuilt for every query word in dataset scoring. | **Improved.** Tokenize each compared metadata value once and use set intersection. No quantitative speed claim or cross-user data caching introduced. |

The URL normalization policy follows the unreserved-character distinction in
[RFC 3986](https://www.rfc-editor.org/rfc/rfc3986#section-6.2.2.2), with more
conservative handling of dots and query bytes. Provenance keeps original URLs.

## Verification

- Baseline: 115 tests, 108 subtests passed before changes.
- Complete post-review suite: **128 tests, 116 subtests passed**, no failures or
  skips. [Output](readiness/review-pytest.log), [JUnit](readiness/review-pytest.xml).
  New defect regressions failed before their fixes. Existing URL/PDF/paper flows,
  safe rendering, simultaneous tab exports, no-request reruns, and empty/failure
  behavior remain covered with mocked HTTP/DNS.
- Compilation, pip check, and git diff whitespace checks passed. No dependency
  upgrade, API server, frontend framework, database, or provider was added.
- At **2026-10-25T03:29:28 UTC**, approved host execution made four real checks:
  example.org working; CIFAR Archive capture found (`20260607155414`); Iris/Fisher
  DataCite results found with correct relative ordering; forest/carbon paper
  search found actual abstract matches. [Raw live evidence](readiness/review-live.json).
  Initial sandbox DNS failures were followed by approved host execution. No mocks
  or result substitutions were used for the saved live evidence.
- All four live operations completed in roughly 0.3–1.3 seconds in that run.
  These observations are not a benchmark, guaranteed latency, replay verification,
  or proof of recovered dataset bytes.

## Remaining work and limits

1. **Strict network deadline remains open.** HTTPX's internal header-reading loop
   can receive incremental bytes inside its inactivity timeout without returning
   to our checkpoints. A deterministic offline reproduction with a 3-second
   budget reaches timeout only after 38 fake seconds; body reads may overshoot by
   one in-flight read. [Diagnostic source](readiness/header-budget-repro.py),
   [output](readiness/header-budget.log). This is not a live network measurement.
   Strict cancellation needs a separately reviewed lower-level transport change;
   no fragile private-backend production wrapper was introduced in this review.
2. **Native PDF parser isolation remains open.** Existing byte/page/text limits
   do not preempt a native extraction hang. Public arbitrary uploads still need
   parser/process-deadline hardening; preflight demonstration papers.
3. **Visual browser acceptance remains open.** Browser tools are unavailable.
   Native Streamlit tests and supplied screenshots support layout/state review,
   not final desktop/mobile visual acceptance or physical browser downloads.
4. **Release source publication remains open.** AGPL files/notices exist; the
   deployed corresponding-source URL and applicable contributor/dependency checks
   still need completion. See LICENSING.md.

Keyword ranking remains heuristic and bounded to retrieved records; it is not
semantic search or a paper-quality score. No source failures, unknown identities,
or archived landing pages are promoted to verified datasets.
