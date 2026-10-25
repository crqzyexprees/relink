"""Deterministic relevance points and explicit, independent match statuses."""

from collections.abc import Iterable
import re
import unicodedata

from relink.candidates import deduplicate_candidates
from relink.identifiers import normalize_doi, normalize_url, url_filename
from relink.models import (Candidate, HashEvidence, MatchStatus, RankedCandidate,
                           RankingEvidence, SearchQuery)


def _tokens(value: str) -> set[str]:
    return set(re.findall(r'\w+', unicodedata.normalize('NFKC', value).casefold()))


def _overlap(query: str, values: tuple[str, ...], *, title_prefix: bool = False) -> float:
    wanted = _tokens(query)
    if not wanted:
        return 0.0
    best = 0.0
    for value in values:
        observed = _tokens(value)
        exact = wanted & observed
        partial = sum(len(word) >= 3 and any(token.startswith(word) for token in observed)
                      for word in wanted - exact) if title_prefix else 0
        best = max(best, (len(exact) + .5 * partial) / len(wanted))
    return best


def _locations(candidate: Candidate) -> tuple[str, ...]:
    return tuple(dict.fromkeys(value for value in (
        candidate.url, candidate.archived_url, *(p.url for p in candidate.provenance)) if value))


def _hash_status(candidate: Candidate, supplied: Iterable[HashEvidence]) -> tuple[bool, bool, list[RankingEvidence]]:
    verified = False
    mismatch = False
    explanations = []
    locations = {normalize_url(url) for url in _locations(candidate)} - {None}
    for evidence in supplied:
        if normalize_url(evidence.candidate_url) not in locations:
            continue
        reference = evidence.reference_sha256.casefold()
        observed = evidence.candidate_sha256.casefold()
        valid = bool(re.fullmatch(r'[0-9a-f]{64}', reference) and re.fullmatch(r'[0-9a-f]{64}', observed))
        independent = bool(evidence.reference_source.strip() and evidence.candidate_source.strip()
                           and evidence.reference_source.strip().casefold() != evidence.candidate_source.strip().casefold())
        if not valid or not independent:
            explanations.append(RankingEvidence('hash', 0, 'Ignored: valid independent SHA-256 evidence was not supplied.'))
        elif reference == observed:
            points = 300 if not verified else 0
            verified = True
            explanations.append(RankingEvidence('hash', points,
                'Caller-supplied reference and independently computed candidate SHA-256 agree.',
                (reference, evidence.reference_source), (observed, evidence.candidate_source)))
        else:
            mismatch = True
            explanations.append(RankingEvidence('hash', -300, 'Independent SHA-256 evidence conflicts.',
                (reference, evidence.reference_source), (observed, evidence.candidate_source)))
    # Contradictory hash observations require investigation, even if one agrees.
    return verified and not mismatch, mismatch, explanations


def rank_candidates(query: SearchQuery, candidates: Iterable[Candidate], *,
                    hash_evidence: Iterable[HashEvidence] = ()) -> list[RankedCandidate]:
    """Scores are raw relevance points, not probabilities or identity proofs.

    Only trusted caller-supplied, independently obtained matching content hashes
    can yield verified_exact_match. Neither provider constructs HashEvidence.
    """
    ranked = []
    hash_evidence = tuple(hash_evidence)
    for candidate in deduplicate_candidates(candidates):
        explanations = []
        similarities = {}
        for signal, requested, values, weight in (
            ('title', query.title, candidate.titles, 30),
            ('author', query.author, candidate.authors, 20),
            ('institution', query.institution, candidate.institutions + ((candidate.publisher,) if candidate.publisher else ()), 10),
            ('description', query.description, candidate.descriptions + candidate.titles, 10),
        ):
            similarities[signal] = _overlap(requested, values, title_prefix=signal == 'title') if requested.strip() else 0.0
            if requested.strip():
                similarity = similarities[signal]
                explanations.append(RankingEvidence(signal, round(weight * similarity),
                    'Whole-word overlap; partial title prefixes count half. Missing metadata contributes zero.',
                    (requested,), values))
        year_match = query.year is not None and query.year == candidate.year
        year_conflict = query.year is not None and candidate.year is not None and not year_match
        if query.year is not None:
            explanations.append(RankingEvidence('year', 10 if year_match else -5 if year_conflict else 0,
                'Publication year matches.' if year_match else 'Publication year conflicts.' if year_conflict else 'Publication year is missing.',
                (str(query.year),), (str(candidate.year),) if candidate.year is not None else ()))
        requested_names = set(query.filenames)
        original_filename = url_filename(query.original_url)
        if original_filename:
            requested_names.add(original_filename)
        filenames = set(candidate.filenames)
        filenames.update(filter(None, (url_filename(url) for url in _locations(candidate))))
        filename_match = bool({name.casefold() for name in requested_names} & {name.casefold() for name in filenames})
        if requested_names:
            explanations.append(RankingEvidence('filename', 10 if filename_match else 0,
                'Exact filename agreement is supporting evidence only.', tuple(sorted(requested_names)), tuple(sorted(filenames))))
        locations = list(_locations(candidate))
        # Archive original_url is API-backed evidence. DataCite original_url is
        # merely the user's search context and must never be scored as a match.
        if candidate.source == 'internet_archive' and candidate.original_url:
            locations.append(candidate.original_url)
        locations.extend(item.identifier for item in candidate.related_identifiers
                         if item.identifier_type.casefold() == 'url' and item.relation_type in ('IsIdenticalTo', 'AlternateIdentifier'))
        url_match = bool(query.original_url and normalize_url(query.original_url) in {
            normalize_url(url) for url in locations} - {None})
        if query.original_url:
            explanations.append(RankingEvidence('url', 50 if url_match else 0,
                'Compared returned resource/identity URLs; availability and file bytes remain unchecked.',
                (query.original_url,), tuple(locations)))
        wanted_doi = normalize_doi(query.doi)
        actual_doi = normalize_doi(candidate.doi)
        doi_match = bool(wanted_doi and wanted_doi == actual_doi)
        if query.doi:
            explanations.append(RankingEvidence('doi', 60 if doi_match else 0,
                'DOI agreement identifies metadata, not independently verified content.',
                (query.doi,), (candidate.doi,) if candidate.doi else ()))
        version_relations = [item for item in candidate.related_identifiers
            if wanted_doi and wanted_doi != actual_doi and normalize_doi(item.identifier) == wanted_doi
            and item.identifier_type.casefold() == 'doi'
            and item.relation_type in ('IsNewVersionOf', 'IsPreviousVersionOf', 'IsVersionOf', 'HasVersion')]
        version_conflict = bool(query.version and candidate.version and query.version.casefold() != candidate.version.casefold()
            and (doi_match or (similarities['title'] >= 0.8 and similarities['author'] >= 0.5)))
        different_version = bool(version_relations or version_conflict)
        if different_version:
            explanations.append(RankingEvidence('version', -20,
                'Explicit version relationship or conflicting version metadata for the identified dataset.',
                (query.doi, query.version), tuple(item.relation_type + ': ' + item.identifier for item in version_relations)
                or (candidate.version,)))
        verified, hash_conflict, hashes = _hash_status(candidate, hash_evidence)
        explanations.extend(hashes)
        supporting = similarities['author'] >= 0.5 or similarities['institution'] >= 0.5 or year_match or filename_match
        likely = not year_conflict and not hash_conflict and (
            doi_match or url_match or (similarities['title'] >= 0.6 and supporting))
        status = (MatchStatus.VERIFIED_EXACT_MATCH if verified else MatchStatus.DIFFERENT_VERSION if different_version
                  else MatchStatus.LIKELY_MATCH if likely else MatchStatus.UNVERIFIED_CANDIDATE)
        ranked.append(RankedCandidate(candidate, sum(item.points for item in explanations), status, tuple(explanations)))
    return sorted(ranked, key=lambda result: (-result.score, normalize_doi(result.candidate.doi) or '',
                                              normalize_url(result.candidate.url or result.candidate.archived_url) or '',
                                              result.candidate.source))
