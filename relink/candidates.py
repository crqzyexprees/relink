"""Conservative candidate deduplication that retains every provider's evidence."""

from dataclasses import replace
from collections.abc import Iterable

from relink.identifiers import normalize_doi, normalize_url
from relink.models import Candidate


def _union(left: tuple, right: tuple) -> tuple:
    # Provenance may contain unhashable metadata dictionaries.
    return left + tuple(value for value in right if value not in left)


def deduplicate_candidates(candidates: Iterable[Candidate]) -> list[Candidate]:
    """Merge the same DOI, or the same URL when both candidates have no DOI.

    Distinct DOIs sharing a landing page remain distinct, as do archive captures
    with different replay URLs. Similar titles are never an identity key.
    """
    merged: list[Candidate] = []
    positions: dict[tuple[str, str], int] = {}
    for candidate in candidates:
        doi = normalize_doi(candidate.doi)
        url = normalize_url(candidate.url or candidate.archived_url)
        key = ('doi', doi) if doi else ('url', url) if url else None
        if key is None or key not in positions:
            if key is not None:
                positions[key] = len(merged)
            merged.append(candidate)
            continue
        index = positions[key]
        previous = merged[index]
        values = {name: _union(getattr(previous, name), getattr(candidate, name)) for name in (
            'titles', 'authors', 'institutions', 'filenames', 'descriptions',
            'related_identifiers', 'evidence', 'provenance')}
        merged[index] = replace(previous, **values,
            url=previous.url or candidate.url, year=previous.year if previous.year is not None else candidate.year,
            publisher=previous.publisher or candidate.publisher, version=previous.version or candidate.version)
    return merged
