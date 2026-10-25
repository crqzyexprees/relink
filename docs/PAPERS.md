# Find papers, then look for their datasets

The app has two native tabs:

1. **Find datasets:** existing URL/PDF extraction and recovery workflow.
2. **Find papers:** enter a topic or describe your research interest, click
   **Find papers**, inspect abstract-ranked results, choose a paper, then click
   **Find datasets from this paper**. Gemini identifies text-supported dataset
   names and DataCite supplies ranked repository records automatically. Select an extracted research link and click
   **Find copies of selected link** to use existing Archive/DataCite recovery.

## Matching method

OpenAlex and the official arXiv API each retrieve up to 15 records per batch from
application-built title/abstract queries. ReLink selects at most 12 meaningful
words from up to 1,200 input characters. DOI/arXiv identities deduplicate records,
retaining source records and filling missing PDF leads; conflicting DOIs stay
separate. Duplicates and missing abstracts can reduce the number below 30.

One Gemini request orders the supplied abstract excerpts against the full topic.
It receives no titles or citation counts, no PDFs, and no authority to create
paper metadata or URLs. Every supplied paper ID must appear exactly once.
ReLink splits real source text into numbered contiguous passages of at most
16 words/240 characters. Gemini chooses a passage ID for each paper and gives a
brief relevance explanation; it does not write quotations. ReLink validates each
reference against that paper's supplied passages and displays the actual source
text. Unknown/duplicate/omitted paper IDs, invalid passage references, added fields,
invalid JSON and incomplete output reject the model ranking. Reasons are bounded
to 240 characters. The explanation remains an AI judgment: selecting a real
passage does not establish that the model's interpretation is correct.

Inputs contain at most 48,000 abstract characters overall, at most 8,000 per
paper, divided evenly across the batch. Text is supplied once as passages;
unquotable tokens longer than 240 characters or containing control characters
are skipped without joining words across the gap. Abstracts with no readable
passages cause explicit keyword fallback. Truncation can hide relevant evidence.
Only the bounded retrieved set is ranked; this is not exhaustive literature
search, a research-quality rating or a calibrated probability. Different wording
can be recognized by Gemini but missed during initial keyword retrieval.

Missing key, quota/authentication errors, timeouts and invalid model data use
explicit keyword fallback. This scores actual abstract whole-word matches at ten
points each, drops zero-match records and treats equal scores as ties. Titles
do not contribute. Missing abstracts cannot be ranked in either mode.

Ten results appear initially. **Load more** reveals the next ten already ranked
papers without provider/model requests or duplicate history entries. Once visible
results are exhausted, **Search more** explicitly fetches the next 15 records
from each source, excludes prior DOI/arXiv/work identities and ranks a new batch.
It replaces the displayed batch and clears selected-paper results; previous
snapshots remain available if private history is enabled. Ranks apply only within
their batch and are never compared as global scores. Maximum: three batches.
Source changes can still cause paging gaps; matching titles alone never merges
preprint/journal versions without identifying evidence.

Provider documentation: [OpenAlex scoped searching](https://help.openalex.org/api/searching/).
OpenAlex paper search needs no API key. Anonymous API usage has a limited free allowance;
quota/rate-limit errors are displayed with Retry-After where supplied, without
automatic retries. See [OpenAlex usage pricing](https://help.openalex.org/access/example-costs/).
The [arXiv API](https://info.arxiv.org/help/api/user-manual.html) supplies metadata,
abstracts and advertised PDF locations. ReLink serializes requests in this process
with at least three seconds between API calls, following its
[terms](https://info.arxiv.org/help/api/tou.html). Multiple worker processes or
replicas would need a shared limiter before scaling this deployment.
One failed source retains the other's usable results with partial status.
The UI displays per-source checks and Retry-After when returned; no retries.

Find papers and Search more send your topic to the sources and the topic/public
abstract excerpts to Google. Use nonconfidential research descriptions. There is
no separate AI toggle. Load more, viewing saved snapshots and unrelated reruns
send nothing. Google Scholar and ResearchGate are not scraped or used as providers.

## What dataset lookup proves

On explicit action, the app:

- Searches DataCite for dataset records whose identifiers mention the paper DOI.
  This preserves source records/DOIs and remains unverified association evidence.
- Extracts public research URLs from the returned abstract.
- Downloads at most one advertised public PDF through the existing public-only
  HTTP client, with a 10 MiB response limit, then uses bounded in-memory extraction.
  Existing page/text/link limits apply. No paper is written to disk by this flow.
- Shows those research links with context; users choose which link to investigate.
  A link may be code, a citation, or a homepage rather than a dataset.
- Runs core Gemini identification on bounded abstract/PDF excerpts using the
  configured key, checks supporting text locally, then searches up to three
  accepted names in DataCite. Named datasets can be discovered without explicit
  links. AI mentions and actual repository candidates are shown separately;
  neither proves original dataset identity or study usage. See [GEMINI.md](GEMINI.md).

A missing DOI, absent abstract/PDF, HTTP error, unsafe redirect, invalid PDF,
429, timeout, and successful empty lookup remain distinct. Metadata failure does
not discard independently extracted PDF links, and PDF failure does not discard
metadata. There is no paywall bypass or recursive reference crawling. The existing
native PDF-parser hang limitation remains; use preflighted papers for the demo.
Model errors/missing key preserve those independent outcomes. Clicking Find
datasets discloses that excerpts go to Google; use public/nonconfidential papers.

Search results and reports persist across ordinary reruns without new requests.
Changing the topic or selected paper clears stale paper dataset results; changing
the selected research link clears its recovery report. The two tabs keep their
reports separate and can both offer evidence downloads without widget collisions.

## Live observations

The [passage-reference fix check](readiness/paper-ranking-grounding-live.json)
used both real source APIs and Gemini: 29 unique records, three missing abstracts,
and **26 accepted ranked papers**. The explicit
[next batch](readiness/paper-ranking-grounding-live-next-batch.json) accepted
**25 unseen papers**, without previous identities repeated. Supporting text comes
from the supplied source passages. These two module-level checks pass; the exact
owner-reported hosted query and updated browser flow remain unverified.

The previous model-written-quote format was brittle: one overlong or paraphrased
quote could reject the entire ranking. Passage references remove the need for
word-perfect quote generation. Other malformed/incomplete output still falls
back honestly, now with a specific safe reason (paper count, unknown/duplicate
ID, invalid passage, overlong explanation, token limit or malformed JSON).
No retries or billing change were added. The owner's supplied quota screenshot
was below its displayed limits; that observation alone does not diagnose a
particular hosted API response.

### Earlier quote-generation format

The separate [30-paper ranking check](readiness/paper-ranking-live.json) used actual
OpenAlex/arXiv responses: 15 records each, 29 unique papers, three missing
abstracts. That latest first-batch model output was rejected and 24 keyword
matches were shown. The explicit [next-batch check](readiness/paper-ranking-live-next-batch.json)
accepted 25 Gemini-ranked unseen papers from the next source pages, with every
short quote checked locally and no identity repeated from the first batch.
An earlier post-prompt check accepted 26 papers; model output remains variable,
and tightening the prompt does not guarantee valid responses. These are module-level
live checks; native UI pagination/dataset handoff is tested separately with mocked
HTTP. A physical hosted-browser run of this upgrade remains unverified.

The first [real attempt](readiness/paper-ranking-live-before-prompt-fix.json)
rejected model output and used keyword fallback. A follow-up diagnostic found
overlong quotes. The prompt requests short fragments; validation limits were
not relaxed. Unsupported output still falls back, and there is no automatic retry.
Sandbox DNS failures are recorded
separately in paper-ranking-live-sandbox.json. None of these reports feeds the UI.

The subsequent Gemini integration has separate [live evidence](readiness/live-gemini.json):
the actual SQuAD paper yielded seven supported names (partial status; five model
quotes replaced with actual local excerpts), with real DataCite results for the
first three. That earlier dataset-identification feature did not itself change
paper ranking; the abstract reranker above is a separate explicit search action.
The historical observation below predates Gemini.

At **2026-10-25T03:10:13 UTC**, the topic
`question answering reading comprehension dataset Stanford` returned ten locally
ranked matches from 25 usable records; four retrieved records lacked abstracts.
The first ranked paper was **Stochastic Answer Networks for Machine Reading
Comprehension**, DOI `10.18653/v1/p18-1157`, with six matched terms (60 points).

The selected advertised ACL PDF was fetched and parsed: 11 pages, six research
links. DataCite returned a valid empty related-dataset result. A selected GitHub
research link reached existing recovery, but Archive returned a real rate limit;
no candidate or successful dataset recovery was invented. That link is a code
repository lead, not a verified dataset. No automatic retry was made.

Saved evidence: [live-paper-discovery.json](readiness/live-paper-discovery.json).
It is a historical live check, never used as app fallback data. API results may
change; this observation does not guarantee future search order or availability.
The HTTP health check for the existing app returned `ok`; browser visual review
of the new tabs remains pending. Native Streamlit tests separately exercise the
full topic → paper → PDF link → ranked recovery/export flow with mocked HTTP/DNS.
