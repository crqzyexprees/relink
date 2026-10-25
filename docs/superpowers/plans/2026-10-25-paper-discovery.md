# Paper discovery implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task, inline in the existing authorized workspace.

**Goal:** Two Streamlit tabs supporting dataset recovery and abstract-ranked paper discovery followed by dataset lookup.
**Architecture:** Separate paper dataclasses, OpenAlex provider, keyword ranking/paper dataset workflow, and thin paper UI; reuse public HTTP, PDF extraction, DataCite, and report rendering.
**Tech Stack:** Existing Python 3.12, Streamlit, HTTPX, PyMuPDF, pytest; no new dependencies.
**Spec:** docs/superpowers/specs/2026-10-25-paper-discovery-design.md.

## Global constraints

- No fabricated data or paid LLM; preserve AGPL notices and provider provenance.
- Public-address validation on every request/redirect; explicit actions only.
- 1,200-character topic; 12 meaningful search words; 25 retrieved papers; 10 ranked papers.
- 10 MiB PDF, existing page/text/link limits; at most one advertised public PDF.

## Review focus

- Missing/malformed abstracts never become abstract matches; bounded inverted indexes.
- Keyword query syntax is application-built, never raw user Boolean expressions.
- Selected paper URLs are untrusted; no internal fetches or automatic reference crawling.
- Provider/PDF failure preserves other available evidence and stays distinct from empty.
- Reruns, new topics, and selection changes never repeat calls or show stale reports.

## Tasks

- [x] 1. Write failing provider/ranking tests; add paper models and OpenAlex adapter,
  reconstruct bounded abstracts, explain keyword ranking, check errors and limits.
- [x] 2. Write failing paper-dataset workflow tests; reuse DOI-related DataCite lookup,
  public PDF download/extraction and abstract links; preserve partial failures.
- [x] 3. Add failing UI tests; split existing workspace into native tabs, implement
  paper search/selection/dataset actions with isolated state and safe rendering.
- [x] 4. Run full suite, live OpenAlex → selected paper → dataset lookup, and existing
  recovery regression checks. Save evidence, update README/STATUS/attribution and demo.

No commits/publishing required. The existing worktree contains substantial user
work; preserve it. Live results are review artifacts, never production fallback data.

Verification: 115 tests and 108 subtests pass; pip check, compileall, whitespace
checks pass. Live OpenAlex search and advertised PDF extraction passed; related
DataCite records were validly empty. Archive returned 429 for the selected research
link; this remains a live service limitation, not a successful recovery. Browser
visual acceptance remains pending. Evidence and decisions: docs/PAPERS.md and STATUS.md.
