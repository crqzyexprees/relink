# Find papers, then look for their datasets

The app has two native tabs:

1. **Find datasets:** existing URL/PDF extraction and recovery workflow.
2. **Find papers:** enter a topic or describe your research interest, click
   **Find papers**, inspect abstract-ranked results, choose a paper, then click
   **Find datasets from this paper**. Gemini identifies text-supported dataset
   names and DataCite supplies ranked repository records automatically. Select an extracted research link and click
   **Find copies of selected link** to use existing Archive/DataCite recovery.

## Matching method

OpenAlex retrieves up to 25 works matching an application-built OR query in titles
and abstracts. ReLink selects at most 12 distinct meaningful words from up to
1,200 characters of input, removes common instruction/stop words, and scores
actual abstract whole-word matches at ten points each. Title/citation count does
not contribute to this local score. Missing abstracts and title-only matches do
not become abstract matches. Up to ten matching papers are displayed; equal
scores are ties. Duplicate DOI/work identities keep their highest-scoring record.

This is explainable keyword matching, not embedding-based semantic similarity,
synonym inference, exhaustive literature search, a research-quality score, or a
calibrated probability. Different inflections and wording can be missed. Only
the bounded retrieved set is reranked. The UI shows matched terms, abstract,
authors, year, source, DOI, and advertised paper/PDF locations.

Provider documentation: [OpenAlex scoped searching](https://help.openalex.org/api/searching/).
OpenAlex paper search needs no API key. Anonymous API usage has a limited free allowance;
quota/rate-limit errors are displayed with Retry-After where supplied, without
automatic retries. See [OpenAlex usage pricing](https://help.openalex.org/access/example-costs/).
The topic is sent to OpenAlex only when Find papers is clicked.

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

## Live observation

The subsequent Gemini integration has separate [live evidence](readiness/live-gemini.json):
the actual SQuAD paper yielded seven supported names (partial status; five model
quotes replaced with actual local excerpts), with real DataCite results for the
first three. This did not change abstract keyword ranking into semantic ranking.
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
