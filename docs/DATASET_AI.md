# Combined dataset discovery

Find datasets now supports **Recover URL**, **Analyze PDF**, and **Search datasets**
(topic/name/DOI). The configured server-side Gemini key is reused automatically on
Find actions. No new key, SDK, database or billing setup is needed. URL/provider
results remain available when Gemini is absent, rate-limited, timed out or invalid.

## What is combined

1. Search real DataCite metadata (requested in relevance order) and, for original
   URLs, Internet Archive. Preserve individual source outcomes, provenance and
   deterministic matching evidence. Search bounds remain explicit.
2. Merge actual repository records from selected-paper DOI associations and
   text-supported dataset names. A PDF's initial URL/DOI/hash evidence survives
   this merge; it is not recomputed using only the paper description.
3. Assess up to30 candidates in one Gemini request. Additional candidates remain
   visible using their existing evidence, with an explicit assessment limit.
   Model output contains only supplied candidate IDs, local evidence references
   and short relevance judgments. Complete ID coverage and own-candidate evidence
   references are required. The model cannot supply candidate URLs or status.
4. Order by independent identity/conflict safeguards, then AI relevance within
   each tier. Verified hashes, exact identifiers and version/hash conflicts remain
   authoritative. Raw evidence scores and verification labels are retained.
   A name-only reported version mismatch is an explicit warning, not proof that
   two records identify the same dataset. No calibrated probability is reported.

Ten candidates appear initially. **Load more datasets** reveals the next ten
cached results without HTTP or Gemini calls. Changing inputs clears stale results.
Named-PDF dataset identification is still a separate existing Gemini call; a
combined relevance batch adds one call, not one call per candidate.

## Exactly what can be sampled

- At most three actual file attempts per assessed batch, one advertised URL per
  candidate. Eligible URLs end in `.csv` or `.tsv` and come from returned locations
  or DataCite `contentUrl`; no guessed links or HTML crawling.
- Stream at most64KiB into the sample buffer, closing at the cap even if the server
  ignores the Range request. Partial ranges must start at byte zero and pass
  range/size checks. Public-only DNS/IP pinning and redirect guards remain.
- UTF-8/BOM delimited tables only, at least two header columns. Parse one header
  and up to three complete logical rows, at most32 columns/240 characters per
  cell. A quoted multiline row counts as one row. A cut-off row or incomplete
  UTF-8 character at the byte cap never becomes fabricated data.
- The sampler retains source, timestamp, byte count, selected response metadata,
  row/header bounds and partial/error status. Cookies/tokens are not recorded.
  Interrupted samples can display earlier complete rows while keeping failure
  status; failed samples are not used as successful model evidence.
- ZIP, Excel, Parquet, JSON, images, HTML landing pages and absent direct URLs use
  metadata only. They are not silently downloaded/converted. Single-column files,
  malformed/binary tables and encoding errors also remain explicit limitations.

Gemini receives bounded real metadata and any eligible header/three rows, capped
at48,000 source characters across the assessed candidates. Long fields/cells can
be shortened; metadata and partial samples may omit critical information. The
first three rows are not statistically representative and never establish full
dataset availability, study use, identity or license permission.

## Privacy, errors and history

Before Find, the UI discloses sending query/public metadata and small samples to
Google. Use public, nonconfidential data. Generation requests retain the 60s read
inactivity/90s cooperative elapsed limits, while samples use5s read/10s elapsed;
these are not strict native/slow-header cancellation guarantees. No retries.

HTTP errors, unsafe addresses/redirects, missing samples and model errors retain
their distinct outcomes. A failed model assessment preserves the original order.
Broad topic queries can still yield weak returned candidates; use a dataset name
or exact DOI when known and read the model's actual relevance explanation.

Snapshots/JSON reports now include bounded sample rows and semantic evidence.
The API key, full datasets, model prompts and PDFs are not saved. Existing private
account authorization and post-request identity rechecks remain unchanged. Old
snapshots decode with defaults. Reopening/exporting a snapshot makes no requests.

## Actual checks

[Exact live evidence](readiness/dataset-ai-exact-live.json) records two separate
checks: an explicitly supplied official public penguin CSV (three rows,15,241
bytes, Gemini source-grounded assessment) and real DataCite discovery of Iris
DOI `10.24432/c56c76` with Gemini assessment. The CSV was a supplied component-test
input, not claimed as an automatically recovered copy. Neither was verified by
hash. The [earlier broad query](readiness/dataset-ai-live.json) returned30 actual
records but weak relevance; its limitations are preserved, not replaced with
demo fixtures. Reports never feed app results. The exact hosted new workflow and
space-theme appearance still need browser acceptance.
