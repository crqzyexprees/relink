# Abstract reranking and pagination implementation plan

> **For agentic workers:** Use superpowers:executing-plans and test-driven-development for this owner-authorized implementation.

**Goal:** Retrieve up to 30 unique papers, rank their actual abstracts with Gemini, and reveal ten at a time.

**Architecture:** Independent OpenAlex/arXiv providers feed deduplication and keyword evidence. One bounded Gemini request returns an ordering of supplied IDs with locally checked abstract quotes. Streamlit owns visibility and explicit next-batch actions; dataset lookup reuses the existing engine.

**Tech stack:** Existing Python, httpx, Streamlit, pytest; standard-library XML. No new dependencies or scraping.

**Spec:** docs/PAPER_SEARCH_NEXT.md, explicitly authorized by the owner's implementation request.

## Global constraints

- Fetch 15 records from each source per batch (up to 30 unique; duplicates/absent abstracts may reduce this).
- Three batches maximum; page/start are application-built. Deduplicate previous batch identities.
- Rank abstract excerpts only, maximum 48,000 characters overall. Preserve original metadata/provenance.
- Accept exactly one ordering of all supplied IDs, each with a short actual abstract quote. Invalid model output, missing key or quota failure gives explicit keyword fallback.
- Show ten initially; Load more reveals ten cached results without requests. Search more retrieves a separately labeled next batch, with fresh ranking relative only to that batch.
- Serialize arXiv API calls with at least three seconds between calls in this process. No automatic retries.
- Retain current history isolation/identity checks and selected-paper dataset workflow. Never interpret relevance as verification or probability.

## Review focus

- Duplicate DOI/arXiv records must retain sources and PDF leads without merging conflicting DOIs.
- Model IDs/quotes may be malformed, incomplete or invented: reject rather than repair relevance evidence.
- One failed source must not suppress the other's real results; errors differ from empty searches.
- Load more, topic changes and account changes must not repeat remote work or expose stale results.
- Persisted older snapshots must decode with defaults; new snapshots retain ranking evidence.

## Task 1: Provider retrieval and abstract ranking

Files: paper_models.py, papers.py, new paper_ranking.py, providers/arxiv.py,
providers/gemini_ranking.py, providers/openalex.py; tests/test_paper_ranking.py.

Interface: search_papers(topic, client=None, settings=None, batch=0,
exclude_identifiers=()) -> PaperSearchResult. New fields have defaults.

- [x] Write mocked integration tests for 30 records, ordering/checked quotes, provenance dedup, partial failures, quota/timeout/malformed model data, pagination and safe XML.
- [x] Run tests and observe missing-feature failures.
- [x] Implement typed outcomes, bounded providers and orchestration.
- [x] Run relevant tests and the full suite; update STATUS.md. Commit at publication.

## Task 2: Streamlit presentation and saved results

Files: paper_ui.py, history_ui.py, tests/test_paper_app.py, history tests.

Interface: result.papers stores a complete ranked batch; session visibility starts at ten.

- [x] Write failing AppTests for cached Load more, source/AI evidence, explicit next batch and dataset handoff.
- [x] Add thin presentation/state handling and current Gemini settings to fresh/saved reruns.
- [x] Verify identity-change/error paths and backward-compatible history snapshots.
- [x] Run full suite, explicit real-service check and update docs/STATUS.
- [ ] Commit and push the tested upgrade.

## Verification

Automated: .venv/bin/python -m pytest; compileall; pip check; git diff --check.
Live: public topic through the actual two providers and configured free-tier Gemini;
record sanitized real outcomes separately. No saved report may feed app results.
Browser automation availability is reported honestly.

## Execution / review record

- Native implementation; no implementation delegation. Provider/model contracts
  feed UI snapshots with defaults preserving older saved records.
- Initial missing-feature/provider/UI tests failed before implementation; focused
  tests and the full suite then passed. Final suite: 191 tests +159 subtests.
- Fresh read-only review found alias loss and skipped-record paging defects.
  Each was reproduced with failing tests, fixed and followed by the full suite.
  No critical/important findings remain; no minor findings were deferred.
- Real APIs returned both source pages. Latest first-batch model data was rejected
  (keyword fallback); next batch accepted 25 unseen papers. Prompt tightening did
  not weaken validation; variable model output remains an explicit limitation.
- Review excluded historical/progress documentation while it was being edited;
  final author pass reconciled current evidence and preserved dated observations.
