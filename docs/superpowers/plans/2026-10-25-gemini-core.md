# Core Gemini dataset identification

Owner authorized Gemini integration by supplying a key, then explicitly requested
it be incorporated into the project rather than an optional side feature.

- [x] Add failing tests and bounded page-text extraction alongside existing PDF
  links (reuse a single parse). Keep page text in session memory, not history.
- [x] Add safe credential configuration (env or git-ignored secrets.toml; never
  print/store keys), a fixed-host Gemini REST provider, and HTTPS POST support
  that does not forward credentials/bodies through redirects. No new dependencies.
- [x] On selected-paper dataset lookup, use Gemini automatically to identify names,
  versions and exact page quotes from bounded text. Validate quoted evidence and
  name/version against the supplied page before accepting any suggestion.
- [x] Search DataCite for at most three accepted names, rank real responses with
  existing models, and show AI mention evidence separately from resource identity.
  The existing DOI/PDF/link recovery paths continue on missing key, 429, or errors.
- [x] Include the same core identification step when Find is clicked on an uploaded
  PDF. Disclose Google text processing before the action, with no automatic API
  calls on upload, tab selection or ordinary reruns. No model-provided URLs/hashes.
- [x] Persist typed mention/results snapshots, not page text or secrets, using
  backward-compatible model defaults. Update saved-result reruns and viewers.
- [x] Test mocked success/hallucination/empty/429/auth/malformed/timeouts/key leaks/
  redirects/history/UI. Run one explicit live public-paper check without printing
  secrets or assuming model access/quota. Update STATUS/docs with actual outcomes.

Default model: a documented free-tier-eligible Gemini text model; model selection
is configurable and must be verified against actual API access. No billing/account
upgrade is authorized. Requests use a Free Tier project as instructed; billing
and quotas are controlled by Google's project settings, not the application.

Bounds: one Gemini generation per explicit paper action, 48,000 supplied text
characters, 8 returned mentions, 240-character/24-word quotes, 3 name searches,
5 repository candidates per name. Existing network/PDF limits remain in effect.
Gemini-suggested mentions are not verified dataset identities or proof of use.

Completed evidence: docs/GEMINI.md, docs/readiness/gemini-pytest.log/xml,
and docs/readiness/live-gemini.json. Full suite: 156 tests/125 subtests passed.
Live identification is partial (five model quotes replaced by real local source
excerpts); seven supported names, three successful DataCite searches.
