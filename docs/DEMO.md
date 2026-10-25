# ReLink demonstration guide

Real tested inputs and their observed outcomes are in
[evaluation.md](evaluation.md). Start with the historical MNIST file URL (observed
404 plus an Archive candidate), then use an Iris DOI for DataCite. Keep failures
and working-URL controls labeled as such.

## Before presenting

Use Python 3.12 on a network-enabled host. Run from the project root:

```bash
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest -q
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8501
```

Keep that terminal running and open http://127.0.0.1:8501. In another terminal:

```bash
.venv/bin/python -m scripts.check_readiness --output docs/readiness/host-live-checks.json
```

Configure the Gemini key privately as shown in [GEMINI.md](GEMINI.md). It is now
part of paper/PDF dataset lookup, with no separate toggle. The existing readiness
script above checks independent URL/PDF/providers; it does not test Gemini. Use
the paper walkthrough below for a fresh model preflight. Never show secrets.toml
or the key during a screen recording.

For saved-history demonstrations, configure native OIDC using [AUTH.md](AUTH.md)
and open `http://localhost:8501` to match the registered callback. Default history
is private and unavailable to guests. Test Alice/Bob accounts separately, close
other tabs when logging out, and never show auth secrets. Legacy shared local
history is not migrated automatically. A trusted single-operator desktop can
explicitly use `RELINK_HISTORY_MODE=local`; never use that mode for shared/public
hosting or describe it as private per-account history.

The diagnostic uses real requests, downloads the public SQuAD paper to a temporary
file if possible, extracts a real link, and runs recovery. It prints PASS/FAIL/BLOCKED
and writes the actual evidence. A nonzero exit means some check did not pass.
The JSON includes the downloaded paper's local path for uploading in the UI.
To use another public paper already on disk:

```bash
.venv/bin/python -m scripts.check_readiness --paper /path/to/paper.pdf --output docs/readiness/host-live-checks.json
```

Only use an input actually extracted from the paper; `--link` can select a specific
extracted URL. There is no fallback to generated papers or cached mock candidates.
Do not present a successful live demo until the host preflight confirms it. The
owner selected AGPL-3.0-only; publish the corresponding release source and configure
RELINK_SOURCE_URL before public deployment. Complete the
[release checklist](LICENSING.md), including contributor and dependency checks.

## Two-minute walkthrough

1. **State the problem:** old papers still exist while dataset locations move or
   disappear. ReLink searches for evidence-backed leads; it cannot guarantee recovery.
2. **Recover URL:** paste `https://doi.org/10.24432/C56C76` and click Find. No description is needed. Explain
   the current URL check and independent provider outcomes. Show returned results
   only if services actually return them. The DOI is automatically used as an
   identity search term, while the original URL and redirects remain in the report.
3. **Inspect a candidate:** show its source/DOI link, capture or retrieval time,
   point contributions, and provenance. Say: metadata agreement can support a
   likely match, but it does not independently verify dataset bytes. Scores are
   relevance points, not percentages.
4. **Analyze PDF:** upload the preflighted public paper and click Find. Show the
   text-supported dataset mentions, page excerpts, and real ranked DataCite
   records. Explain locally replaced quotes/partial status where shown. An
   extracted link can also run existing URL recovery. A readable link-free PDF
   can use identification too; no dataset description is required. Display the
   observed result, including genuine model/quota/empty/failure outcomes.
5. **Export (optional):** explain that JSON saves machine-readable search evidence,
   not dataset bytes. Download the report and show its original URL, independent
   provider statuses, evidence, and verification limitations. Changing inputs clears
   old results; downloading does not repeat the network search.

## Topic → paper → datasets walkthrough

1. Open **Find papers**, enter `question answering reading comprehension dataset Stanford`,
   and click **Find papers**. Explain that up to 30 retrieved papers are ranked
   against their actual abstract excerpts by Gemini, with checked supporting
   quotes. Show the model/source statuses; keyword fallback is explicit if needed.
   **Load more** reveals the next ten cached results without another API call.
   After the batch is visible, **Search more** retrieves a separately ranked new
   batch; ranks apply within each batch, not across all literature.
2. Choose an actual returned paper and inspect its abstract, matched keywords,
   DOI, and source. Click **Find datasets from this paper** to search related
   metadata, extract links from an advertised public PDF if available, and run
   Gemini identification automatically. Show names supported by actual excerpts,
   then the independent repository searches and verification limits. Model errors
   leave the independent DOI/PDF/link results visible.
3. Inspect actual metadata or select a research link and click **Find copies of
   selected link**. Explain that research links can be citations/code and that a
   metadata association does not prove the paper used a particular dataset.
4. Show genuine empty, missing-PDF, or rate-limit outcomes when they occur.
   See [PAPERS.md](PAPERS.md) for saved live evidence and limits. The observed
   live lookup parsed a real PDF; its final Archive lookup was rate-limited.

## Honest failure demonstration

- A deliberately malformed PDF should produce an error and leave Find disabled.
- `https://httpbin.org/status/404` is a live 404 probe, not an academic dataset.
  Show its observed status; an unavailable probe service is a service failure.
- If a provider returns 429, show Retry-After and wait. Do not repeatedly click
  Find to force service rate limiting.
- If DNS, timeout, or provider errors occur, show the source checks and export the
  failed report. Do not call that “not found” or replace it with sample candidates.

## If venue networking is unavailable

Use the offline test evidence in [READINESS.md](READINESS.md), clearly labeled as
mocked. Explain the live blocker and show real PDF extraction only if the actual
paper is available locally. Do not run fixture data through the public UI or
describe mocked successes as recovered resources.

## Clean-install preflight

These commands leave the working `.venv` untouched. Use an unrestricted host and
stop if any step fails:

```bash
relink_clean_dir=$(mktemp -d /tmp/relink-clean.XXXXXX)
python3.12 -m venv "$relink_clean_dir/venv"
"$relink_clean_dir/venv/bin/python" -m pip install -r requirements.txt
"$relink_clean_dir/venv/bin/python" -m pip check
"$relink_clean_dir/venv/bin/python" -m pytest -q
```

These instructions have now succeeded in an isolated /tmp environment using
approved network access: all 95 tests and pip check passed. See
readiness/clean-install.log, clean-pytest.log, and clean-environment-final.log.
