# Implemented paper-search improvement

Owner discussion, 2026-10-25: prioritize improved paper relevance before Auth0
configuration. Subsequently authorized and implemented on 2026-10-25; this document
records the design. Current behavior/evidence: [PAPERS.md](PAPERS.md).

## Flow

1. Search topic/description keywords in OpenAlex plus arXiv (15 records each per batch), retaining actual
   abstracts, paper IDs, DOIs, authors, dates, source and advertised PDF links.
2. Deduplicate the bounded retrieved set to at most 30 unique papers, retaining
   all source provenance. The number is a cap, not a promise that 30 exist.
3. Ask Gemini to rerank supplied abstracts against the research request, using
   bounded inputs and structured paper IDs/reasons. Accept only supplied IDs;
   Gemini selects numbered passages split from actual abstract excerpts, and
   ReLink displays that source text. Reject invalid references. Do not let the
   model invent papers, URLs, dataset identity or unsupported relevance claims.
4. Display the top ten from the retrieved set, with keyword signals and actual
   abstract evidence. Relevance is not paper quality or a calibrated probability.
   Keep an explicit keyword fallback when the model/key/quota is unavailable.
5. Load more first reveals the next ten already ranked papers with no extra
   provider/model calls. Once the batch is exhausted, a separately explicit
   Search more action retrieves unseen papers and discloses a separately ranked
   new batch, replacing the view. Three batches maximum; saved snapshots retain
   earlier batches when private history is enabled.
6. A selected paper reuses current public-PDF parsing, Gemini dataset mentions
   and real repository discovery. Do not download/analyze 30 full PDFs to decide
   abstract relevance. Missing abstracts/full text remain honest limitations.

Batch-only ranks are relative to that batch; future fetching must not silently
compare unrelated per-batch ranks as globally calibrated scores. Preserve stable
ordering within a displayed snapshot and label any refreshed ranking.

## Source choices

- arXiv provides an official search/metadata API with abstracts and paging:
  https://info.arxiv.org/help/api/user-manual.html. Follow its usage limits.
- Retain current OpenAlex coverage and independent provenance.
- Google Scholar says automated access must respect robots.txt and offers no bulk
  access: https://scholar.google.com/intl/en/scholar/help.html. Use it manually;
  it is not integrated as an automatic provider.
- ResearchGate's terms section 4.2 restrict scripted access/scraping:
  https://www.researchgate.net/terms-of-service. Keep as a manual external link
  unless a suitable authorized integration is arranged.

Implemented with no new dependencies. Gemini ranks only real supplied abstracts;
it separately identifies dataset mentions after a paper is selected. Initial
retrieval remains keyword-based and source-bounded. Model errors preserve honest
keyword fallback. No Google Scholar/ResearchGate scraper was added.
