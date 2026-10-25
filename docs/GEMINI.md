# Core paper-to-dataset identification

Gemini runs automatically on explicit **Find** in Analyze PDF and **Find datasets
from this paper** in Find papers. There is no separate AI toggle. Uploading a file,
opening a tab, viewing history, and ordinary Streamlit reruns make no Gemini
requests. URL-only recovery and abstract keyword ranking do not need a model.

**Paper relevance ranking:** Find papers and Search more now also call Gemini
automatically, using up to 30 real abstract excerpts and the topic. It orders
supplied IDs with checked short quotes; titles, full PDFs and citation counts are
not sent for ranking. Ten results appear initially; Load more reveals cached
results without model calls. Keyword ranking remains the fallback on missing key,
model errors or unsupported output. See [paper ranking and limits](PAPERS.md).

## Configuration

Use your intended free-tier Google AI Studio project. Put top-level values in the
git-ignored `.streamlit/secrets.toml`:

```toml
GEMINI_API_KEY = "YOUR_KEY"
GEMINI_MODEL = "gemini-3.5-flash-lite"
```

Environment variables override these values. `.env.example` is documentation;
the app does not load `.env` automatically. Keys stay server-side, are omitted
from settings repr, and are never included in reports/history. Authenticated
requests use an HTTPS header to the fixed Google endpoint. Redirects are rejected
without forwarding their credential or body. No Google SDK or dependency was added.

The live project rejected the initial 2.5 model with HTTP 404. The default is now
3.5 Flash-Lite, which worked with this key. Google lists it as free-tier eligible;
new projects may lack older model access. Actual billing/quotas depend on the
Google project, which ReLink does not inspect or change. No billing upgrade or
paid account action was performed. See [models](https://ai.google.dev/gemini-api/docs/models),
[pricing and data use](https://ai.google.dev/gemini-api/docs/pricing), and
[generateContent API](https://ai.google.dev/api/generate-content).

## Evidence and limits

1. Reuse locally extracted PDF text; selected papers may also supply an abstract.
   Send at most 48,000 characters total, 8,000 per supplied page, in one generation
   per explicit action. The UI discloses Google text processing before Find.
   Use public/nonconfidential papers; free-tier data-use terms apply.
2. Request up to eight names, versions, page numbers and short quotes. Reject
   unsupported names, pages, versions, malformed responses and added URL/hash
   fields. Schema conformance alone is insufficient evidence.
3. Check each quote against the supplied page. If a model paraphrases a quote,
   reject that quote; only when the name occurs on the claimed page can ReLink
   extract an actual contiguous source excerpt locally. These replacements are
   labeled `local_text`, warned about and returned as a partial identification.
   Excerpts are limited to 240 characters/24 words and whitespace is normalized.
4. Search the first three accepted names in DataCite, at most five real returned
   candidates each. Rank with existing evidence rules, preserving DOI, URL,
   provenance, version conflicts and verification status. Model output never
   supplies a recovered resource. The remaining names remain visible as mentions.

A textual mention is not proof that a paper used that dataset, that a repository
record is the original version, or that files survive. Names in related-work
sections can be identified too. Relevance points are not probabilities. No model
or metadata agreement can create verified-exact-match status without independent
identifying evidence. Matching study usage and file/version identity still needs
human review. PDF truncation and bounded repository searches can miss results.

Missing credentials, no text, valid empty output, invalid output, authentication
errors, 429 with Retry-After, timeouts and service errors stay distinct. No automatic
retry is made. Independent DOI/PDF/link outcomes remain available on model failure.
One invalid repository query cannot discard other results.

Reports/history store typed identification and repository snapshots, short quoted
evidence and timestamps. They do not store the key, model prompt, full page text
or PDF bytes. An uploaded-PDF-only snapshot needs a reupload to rerun because the
original text is intentionally absent. Existing snapshots remain readable.

## Verification

Full mocked suite: **156 tests and 125 subtests passed**, no skips/failures.
See [output](readiness/gemini-pytest.log) and [JUnit](readiness/gemini-pytest.xml).
Native Streamlit tests exercise both core actions, link-free uploads, saved views,
safe rendering, credential isolation, and request-free reruns. Provider tests cover
grounding, malformed/empty responses, auth errors, 429, timeouts, redirects, size
limits and partial failures. Tests never use the owner's actual key or live API.

The separate [live SQuAD paper check](readiness/live-gemini.json) used the actual
public [arXiv paper](https://arxiv.org/abs/1606.05250), not a generated fixture.
Gemini returned seven accepted names: SQuAD, ImageNet, Penn Treebank, MCTest,
WikiQA, Children's Book Test, and BAbI. Five model quotes were replaced by real
locally extracted excerpts, so the status remains **partial**. DataCite returned
five repository records for each of the first three names. These are candidate
records, not fifteen recovered datasets; file identity/availability was not checked.
Earlier failed-model and grounding diagnostics remain separately saved.

To repeat visibly, upload that public PDF in Analyze PDF and click Find; inspect
the identification status, excerpt labels and real source records. Or choose a
public returned paper in Find papers and click Find datasets from this paper.
Outputs/order can change with services. Browser visual acceptance remains pending;
AppTest and this live module check do not substitute for a manual browser run.

The latest [live first batch](readiness/paper-ranking-live.json) retrieved actual
OpenAlex/arXiv records but rejected Gemini output and used keyword fallback.
The explicit [next batch](readiness/paper-ranking-live-next-batch.json) accepted
25 unseen papers with locally checked quotes. Model output can still fail
validation; prompt tightening did not relax the checks. There are no automatic
retries or hardcoded replacements.
