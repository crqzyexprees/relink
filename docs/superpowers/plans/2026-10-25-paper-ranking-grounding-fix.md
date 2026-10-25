# Paper ranking grounding reliability fix

**Scope:** Owner reported hosted `Gemini ranking: invalid response`. Fix existing
ranking reliability, preserve evidence checks and independent fallback. No dataset
discovery extension, paid services, extra API retries or dependencies.

**Evidence:** Current client collapses incomplete JSON, invalid IDs and bad/overlong
model quotes into one generic status. Earlier real diagnostics found overlong
quotes; latest replay on public abstracts succeeded, confirming intermittency.
Owner's quota screenshot shows usage below displayed limits; this does not establish
the exact rejection reason for their hosted request. HTTP 429 is a separate path.

**Change:** Segment the same bounded real abstract text into numbered passages,
each at most 16 words/240 characters. Gemini returns paper ID, evidence passage ID
and brief reason; evidence text is selected locally from that paper's supplied
passages. Complete paper-ID coverage and valid own-paper passage references remain
mandatory. Do not accept free-form model quotations. Preserve typed result/history
contracts and one request per explicit search. Give safe, specific rejection
details without storing/echoing raw model responses or credentials.

- [x] Add failing provider regressions for referenced source passages, invalid
  references, response diagnostics, short/Unicode/long-token abstracts and bounds.
- [x] Implement passage-grounded output and adapt existing mocked provider/UI
  fixtures to the new documented API contract. Keep unknown IDs/extra fields,
  missing papers, rate limits/timeouts and malformed data covered.
- [x] Run focused and full suite, live public search, independent read-only review;
  update STATUS and current docs. No hosted browser verification is inferred.
- [x] Commit/push the tested fix under existing publication authorization: 08601df,
  confirmed pushed to GitHub main.

**Verification:** 203 tests +169 subtests pass with no failures/skips. Real first
and second batches accepted 26 and 25 ranked papers, respectively. Independent
review found no critical/important defects; its additional boundary probes were
persisted as regression tests. Compileall, pip check, whitespace and configured-key
exclusion checks pass. Exact hosted request/browser acceptance remains unverified.
