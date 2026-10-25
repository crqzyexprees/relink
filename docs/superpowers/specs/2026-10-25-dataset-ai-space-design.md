# Dataset evidence ranking and space workspace

Owner authorizes two changes after confirming hosted paper search works:
combine Gemini with existing dataset recovery/discovery, using metadata/headers
and roughly three sample rows; refresh the UI with an enjoyable space theme.
Owner delegates practical improvements; implementation proceeds without a new
approval round. Original ReLink licensing/safety/history rules remain binding.

## Dataset workflow

- Keep URL and PDF recovery, add direct dataset topic/name/DOI search in the same
  tab. Use real Archive/DataCite results, deduplicate and retain deterministic
  evidence scores/statuses. Up to30 candidates, ten initially, cached Load more.
- Gemini is part of explicit dataset Find actions with the existing saved key.
  Combine metadata relevance with existing rules; never replace verification or
  promote a conflicting version/hash above an independently identified match.
  No model-generated candidates, URLs, hashes or verification claims.
- Before action disclose sending query, public metadata and bounded samples to
  Google. One semantic-ranking call per combined result batch, not per candidate.
  Missing key/rate limit/timeout/invalid output preserves independent results.
- Preview at most three advertised direct CSV/TSV URLs per batch, one per
  candidate, at most64KiB each, bounded public-only streaming requests, no cookies
  or credentials. Range hints are not trusted to enforce the cap. Do not crawl
  HTML, unpack archives, parse spreadsheets or download entire datasets.
- Parse only header and up to3 complete logical rows, bounded columns/cells;
  a partial row at the byte boundary must not become data. Preserve fetch source,
  time, byte count and partial/sample status. Content/identity remains unverified.
- For other formats/absent direct URLs, use metadata only with an explicit reason.
  Prompt and responses use supplied IDs and numbered actual-source evidence,
  following the hardened paper ranking pattern. No free-form model quotations.
- Keep all result/evidence/preview snapshots typed, backwards-compatible and
  exportable. No new shared history; recheck account identity after remote work.

## Connected flow

URL/topic searches rank a combined candidate batch. Paper/PDF dataset mentions
still come from existing extraction; consolidate their actual repository results
for one semantic ordering, retaining independent related-record/link outcomes.
Dataset recovery from a selected research link uses the same combined engine.

## Visual direction

Original deep-space research cockpit inspired by the mood of Project Hail Mary,
without movie imagery, branding or copied artwork. Midnight navy, amber primary
buttons, cyan evidence accents, soft stars/orbital lines and gentle gradient fades.
Hero: ReLink / Follow the signal. Reconnect your research. Native controls stay
plain and clear. Hover/focus cues and optional subtle motion respect reduced-motion
settings. Responsive layout, readable contrast, no fake counters/progress/results
or decorative controls masquerading as functional features. No external fonts,
images, new frontend framework or dependencies.

## Alternatives considered

Metadata-only ranking is simpler but cannot inspect schemas; unrestricted file
downloads would exceed the owner's sample-only requirement. Use bounded CSV/TSV
sampling with metadata fallback. Retain the existing Streamlit architecture;
implement the visual theme in application-owned CSS, independently of the engine.

## Acceptance

Mock HTTP/DNS/model tests exercise preview caps and malformed/truncated files,
safe redirects, missing samples, complete ID/evidence ordering, authoritative
identity/version guards, errors and fallback. AppTests cover topic/URL/PDF and
selected-paper dataset flows, safe rendering, exports, cached pagination and
history scope. Explicit real public checks are separate. Browser appearance is
reported unverified if no browser executor is available.
