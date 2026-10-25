# Bounded Gemini generation timeouts

Owner reports paper ranking `timeout`. Code inspection finds every Gemini POST
inherits ordinary web limits: 10s inactivity, 30s cooperative elapsed budget.
This can abort a valid slow generation. Exact hosted timing/query is unknown.

Give only Gemini generation requests a 60s read-inactivity allowance and 90s
cooperative elapsed budget, retaining 10s DNS/connect/write/pool limits. Ordinary
GET/default POST behavior stays unchanged. No retries, billing change, new model,
or relaxation of ID/evidence checks. Keep the documented slow-header cancellation
limitation; this is not a strict wall-clock guarantee.

- [x] Add failing slow-generation and request-budget regressions with fake time.
- [x] Add validated per-POST read/elapsed overrides; apply to both Gemini flows.
- [x] Run focused/full tests, record separate real timing observations, review.
- [ ] Update STATUS/docs; commit and push under prior publication authorization.

Verification: 209 tests +181 subtests pass. Actual before/after calls accepted26
papers in3.793/3.369 seconds; observed read limit changed10→60 with other phases10.
Exact hosted delay not reproduced. Independent review: no important findings.
Known cooperative slow-header cancellation limitation remains explicitly open.
