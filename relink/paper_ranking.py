"""Local abstract keyword evidence and conservative cross-source paper identity."""
from dataclasses import replace
import re
import unicodedata

from relink.identifiers import normalize_doi
from relink.paper_models import PaperProvenance, RankedPaper
from relink.providers.arxiv import arxiv_identifier


def keyword_rank(paper, terms):
    words = set(re.findall(r'[^\W_]+', unicodedata.normalize('NFKC', paper.abstract).casefold()))
    matched = tuple(term for term in terms if term in words)
    return RankedPaper(paper, len(matched) * 10, matched, terms)


def paper_identities(paper):
    identities = {paper.id}
    if paper.doi: identities.add('doi:' + (normalize_doi(paper.doi) or paper.doi))
    urls = (paper.id, paper.landing_url, paper.pdf_url,
            *(url for p in paper.provenance for url in (p.record_url, p.landing_url, p.pdf_url)))
    for url in urls:
        arxiv_id = arxiv_identifier(url)
        if arxiv_id: identities.add('arxiv:' + arxiv_id)
    identities.update(p.record_url for p in paper.provenance)
    return identities - {''}


def deduplicate_papers(papers, terms):
    unique = []
    for paper in papers:
        if not paper.provenance:
            paper = replace(paper, provenance=(PaperProvenance(paper.source, paper.id, paper.retrieved_at,
                                                              paper.landing_url, paper.pdf_url),))
        index = 0
        while index < len(unique):
            other = unique[index]
            if paper.doi and other.doi and normalize_doi(paper.doi) != normalize_doi(other.doi):
                index += 1
                continue
            if paper_identities(paper) & paper_identities(other):
                # Retain the strongest lexical abstract, then fill missing metadata.
                best, rest = (paper, other) if keyword_rank(paper, terms).score > keyword_rank(other, terms).score else (other, paper)
                paper = replace(best, doi=best.doi or rest.doi, pdf_url=best.pdf_url or rest.pdf_url,
                    landing_url=best.landing_url or rest.landing_url, abstract=best.abstract or rest.abstract,
                    authors=best.authors or rest.authors, year=best.year or rest.year,
                    arxiv_id=best.arxiv_id or rest.arxiv_id,
                    provenance=tuple(dict.fromkeys((*other.provenance, *paper.provenance))))
                unique.pop(index)
                # A bridge can connect two previously distinct source groups.
                index = 0
                continue
            index += 1
        unique.append(paper)
    return tuple(unique)
