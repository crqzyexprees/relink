"""Bounded samples plus AI relevance, subordinate to independent identity evidence."""
from dataclasses import replace
from datetime import datetime, timezone

from relink.dataset_models import DatasetAssessment
from relink.dataset_preview import preview_candidate
from relink.gemini_config import GeminiSettings
from relink.identifiers import normalize_doi, normalize_url
from relink.models import DiscoveryResult, MatchStatus, RankingEvidence
from relink.providers.gemini_datasets import rank_dataset_metadata
from relink.ranking import rank_candidates


def candidate_id(candidate):
    return normalize_doi(candidate.doi) or normalize_url(candidate.url or candidate.archived_url or '') or candidate.source


def _tier(item):
    if item.status == MatchStatus.VERIFIED_EXACT_MATCH: return 0
    if any(e.signal == 'hash' and e.points < 0 for e in item.explanation): return 4
    if item.status == MatchStatus.DIFFERENT_VERSION or any(e.signal == 'requested_version' for e in item.explanation): return 3
    if any(e.signal in ('doi', 'url') and e.points > 0 for e in item.explanation): return 1
    return 2


def assess_datasets(query, ranked, *, client, settings=None):
    settings = settings or GeminiSettings()
    original = tuple(ranked)
    ranked, tail = original[:30], original[30:]
    if not ranked or not settings.api_key:
        return original, DatasetAssessment('not_found' if not ranked else 'not_configured',
            'No candidate records to assess.' if not ranked else 'Gemini is not configured; existing evidence order retained.',
            settings.model, datetime.now(timezone.utc).isoformat())
    previews, sampled = [], 0
    for item in ranked:
        preview = None
        if sampled < 3:
            preview = preview_candidate(item.candidate, client=client)
            preview = replace(preview, candidate_id=candidate_id(item.candidate))
            if preview.status != 'metadata_only': sampled += 1
        previews.append(preview)
    ordered, assessment = rank_dataset_metadata(query, ranked, tuple(previews), settings=settings, client=client)
    if tail:
        assessment = replace(assessment, warnings=assessment.warnings +
            (f'AI assessment limited to 30 candidates; {len(tail)} additional candidate(s) retained with existing evidence.',))
    if assessment.status == 'ranked':
        tail_positions = {candidate_id(item.candidate): i for i, item in enumerate(tail)}
        ordered = tuple(sorted((*ordered, *tail), key=lambda item: (_tier(item),
            item.ai_rank if item.ai_rank is not None else 31 + tail_positions.get(candidate_id(item.candidate), 0))))
    else:
        ordered = original
    return ordered, assessment


def combine_dataset_results(query, results, *, settings, client, initial=None, prior_ranked=()):
    """Merge actual lookup records without repeating provider/model requests per name."""
    providers = tuple(initial.providers if initial else ()) + tuple(r for r in results if r.status != 'not_applicable')
    candidates = tuple(item.candidate for item in initial.candidates) if initial else ()
    candidates += tuple(c for result in results for c in result.candidates)
    ranked = tuple(rank_candidates(query, candidates))
    remembered = {}
    for item in (*(initial.candidates if initial else ()), *prior_ranked):
        remembered.setdefault(candidate_id(item.candidate), []).append(item)
    preserved = []
    for item in ranked:
        records = remembered.get(candidate_id(item.candidate), ())
        if not records:
            preserved.append(item)
            continue
        hash_conflicts = [r for r in records if any(e.signal == 'hash' and e.points < 0 for e in r.explanation)]
        best = min(hash_conflicts or records, key=lambda row: (_tier(row), -row.score))
        warnings = tuple(e for record in records for e in record.explanation if e.signal in ('version', 'requested_version'))
        extra = tuple(replace(e, points=0) for e in warnings if e not in best.explanation)
        status = best.status
        if hash_conflicts: status = MatchStatus.UNVERIFIED_CANDIDATE
        elif status != MatchStatus.VERIFIED_EXACT_MATCH and any(r.status == MatchStatus.DIFFERENT_VERSION for r in records):
            status = MatchStatus.DIFFERENT_VERSION
        preserved.append(replace(best, candidate=item.candidate, status=status, explanation=best.explanation + extra))
    ranked = tuple(preserved)
    ranked, assessment = assess_datasets(query, ranked, settings=settings, client=client)
    errors = any(result.status not in ('found', 'not_found') for result in providers)
    status = ('partial' if errors else 'found') if ranked else ('error' if errors else 'not_found')
    return DiscoveryResult(status, ranked, providers, 'Merged source records; samples and metadata do not verify dataset identity.', assessment)
