# Topic → papers → datasets

The owner's requested layout is two tabs: Find datasets retains URL/PDF recovery;
Find papers takes a topic or description, matches papers on abstract keywords,
and offers dataset lookup for a selected paper. No paper title is required.

Use OpenAlex for bounded title/abstract retrieval, then rank only papers with
actual matching abstract words locally. Show abstract, matched terms, score,
authors, year, DOI/source links, and missing-abstract counts. Scores are relevance
points across retrieved papers, not quality ratings or probabilities. Keyword
matching is the initial implementation, not semantic/synonym inference.

Approaches considered: provider semantic search versus provider retrieval with
local abstract keyword scoring. The user's keyword-matching scope supports the
latter: it is transparent, requires no embedding dependency/paid LLM, and lets
tests prove title-only matches cannot rank. Synonym-aware semantic search is deferred.

Dataset lookup explicitly searches DataCite for records related to the paper DOI
and optionally downloads one advertised public PDF through the existing public-only
transport. Extracted PDF/abstract links remain research links, not proven datasets.
The user selects a link to run the existing recovery engine in the papers tab.
No paywall bypass, HTML scraping, automatic crawling of links, or PDF storage.

UI and network/ranking code remain separate. Both tabs preserve their own state;
no requests happen on tab changes or ordinary reruns. Changed topics/selections
clear stale results. Untrusted values render as text; links pass public-link checks.
All requests are bounded; PDF downloads use the existing 10 MiB limit. The known
native-parser hang limitation still applies. Errors/429/empty/missing PDFs are
shown honestly; actual live calls and mocked tests remain separate.
