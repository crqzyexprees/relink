"""Explicit live review probes. Never imported by the app or automated tests.

Run on a network-enabled host: python -m scripts.check_readiness
Use --paper /path/to/public-paper.pdf to supply a real paper already downloaded.
"""

import argparse
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile

import httpx

from relink.extraction import MAX_PDF_BYTES, PDFExtractionError, extract_pdf_links
from relink.models import SearchQuery
from relink.network import PublicHTTPClient, RequestFailure
from relink.providers.datacite import DataCiteProvider
from relink.providers.internet_archive import InternetArchiveProvider
from relink.verification import check_current_url
from relink.workflow import run_recovery


PAPER_URL = 'https://arxiv.org/pdf/1606.05250'
ARCHIVE_INPUT = 'https://stanford-qa.com/'


def provider_verdict(status):
    if status in ('found', 'not_found'):
        return 'PASS'
    return 'FAIL' if status == 'invalid_response' else 'BLOCKED'


def run_checks(paper: Path | None = None, selected_url: str | None = None) -> dict:
    paper_source = str(paper) if paper else PAPER_URL
    evidence = {'checked_at_utc': datetime.now(timezone.utc).isoformat(),
                'mode': 'live_no_mocks', 'checks': {}}
    checks = evidence['checks']
    with PublicHTTPClient(max_body_bytes=MAX_PDF_BYTES) as client:
        for name, url, expected in (
            ('valid_url', 'https://example.org/', 'working'),
            ('broken_url', 'https://httpbin.org/status/404', 'not_found'),
        ):
            result = check_current_url(url, client)
            verdict = 'PASS' if result.status == expected else 'BLOCKED' if result.status in (
                'dns_failure', 'timeout', 'network_error', 'rate_limited', 'forbidden', 'blocked') else 'FAIL'
            checks[name] = {'verdict': verdict, 'input': url, 'expected': expected, 'result': asdict(result)}
        archive = InternetArchiveProvider(client).search(ARCHIVE_INPUT)
        checks['internet_archive'] = {'verdict': provider_verdict(archive.status),
                                      'input': ARCHIVE_INPUT, 'result': asdict(archive)}
        datacite = DataCiteProvider(client, limit=3).discover(SearchQuery(doi='10.24432/C56C76'))
        checks['datacite'] = {'verdict': provider_verdict(datacite.status),
                              'input': '10.24432/C56C76', 'result': asdict(datacite)}
        try:
            if paper:
                if paper.stat().st_size > MAX_PDF_BYTES:
                    raise PDFExtractionError('The supplied paper exceeds 10 MiB.')
                content = paper.read_bytes()
            else:
                response = client.fetch(PAPER_URL, read_body=True)
                if response.http_status != 200:
                    checks['real_pdf'] = {'verdict': 'BLOCKED', 'source': PAPER_URL,
                                          'http_status': response.http_status,
                                          'detail': 'The public paper could not be downloaded.'}
                    content = None
                else:
                    content = response.body
                    with tempfile.NamedTemporaryFile(prefix='relink-public-paper-', suffix='.pdf', delete=False) as downloaded:
                        downloaded.write(content)
                        paper = Path(downloaded.name)
            if content is not None:
                extraction = extract_pdf_links(content)
                if not extraction.links:
                    raise PDFExtractionError('No selectable public URL was extracted from the real paper.')
                link = next((item for item in extraction.links if item.url == selected_url), None) if selected_url else extraction.links[0]
                if link is None:
                    raise PDFExtractionError('The requested link was not extracted; no substitute was invented.')
                report = run_recovery(SearchQuery(original_url=link.url), client=client,
                    input_context={'mode': 'pdf', 'paper_source': paper_source,
                                   'filename': paper.name if paper else 'public-paper.pdf',
                                   'document_sha256': hashlib.sha256(content).hexdigest(),
                                   'selected_link_page': link.occurrences[0].page})
                operational = report.discovery.status in ('found', 'not_found')
                invalid_response = any(provider.status == 'invalid_response' for provider in report.discovery.providers)
                checks['real_pdf'] = {'verdict': 'PASS' if operational else 'FAIL' if invalid_response else 'BLOCKED',
                    'source': paper_source, 'local_path': str(paper),
                    'sha256': hashlib.sha256(content).hexdigest(), 'page_count': extraction.page_count,
                    'link_count': len(extraction.links), 'selected_url': link.url,
                    'extraction_warnings': list(extraction.warnings), 'report': asdict(report)}
        except RequestFailure as exc:
            checks['real_pdf'] = {'verdict': 'BLOCKED', 'source': PAPER_URL,
                                  'status': exc.status, 'detail': exc.detail,
                                  'stage': 'download', 'engine_recovery_run': False}
        except (PDFExtractionError, OSError) as exc:
            checks['real_pdf'] = {'verdict': 'FAIL' if paper else 'BLOCKED', 'source': str(paper or PAPER_URL),
                                  'detail': str(exc), 'engine_recovery_run': False}
    try:
        with httpx.Client(trust_env=False, timeout=3) as health:
            response = health.get('http://127.0.0.1:8501/_stcore/health')
        checks['streamlit_health'] = {'verdict': 'PASS' if response.status_code == 200 else 'FAIL',
                                      'http_status': response.status_code, 'body': response.text[:100]}
    except httpx.HTTPError as exc:
        checks['streamlit_health'] = {'verdict': 'BLOCKED', 'error_type': type(exc).__name__, 'detail': str(exc)}
    return evidence


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--paper', type=Path)
    parser.add_argument('--link', help='Optional exact link to select from the actual paper.')
    parser.add_argument('--output', type=Path, default=Path('docs/readiness/live-checks.json'))
    args = parser.parse_args(argv)
    evidence = run_checks(args.paper, args.link)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2, allow_nan=False) + '\n')
    for name, check in evidence['checks'].items():
        result = check.get('result', {})
        print(f"{name}: {check['verdict']} {result.get('status', check.get('status', check.get('detail', '')))}")
    print(f'Evidence: {args.output}')
    return 0 if all(item['verdict'] == 'PASS' for item in evidence['checks'].values()) else 1


if __name__ == '__main__':
    raise SystemExit(main())
