"""Offline bounds and provenance tests for public CSV/TSV samples."""
import importlib.util


def test_preview_contracts_are_available_without_candidate_dependencies():
    assert importlib.util.find_spec('relink.dataset_models') is not None

import httpx
import pytest
from unittest.mock import patch

from relink.models import Candidate, CandidateProvenance
from relink.network import PublicHTTPClient, RequestFailure


PUBLIC_IP = '93.184.215.14'


def public_client(handler, **kwargs):
    return PublicHTTPClient(transport=httpx.MockTransport(handler),
                            resolver=lambda host, port: [PUBLIC_IP], **kwargs)


def test_prefix_stops_stream_at_cap_even_when_range_is_ignored():
    chunks, closed, requests = [], [], []

    class Stream(httpx.SyncByteStream):
        def __iter__(self):
            for i in range(30):
                chunks.append(i)
                yield b'x' * 4096
        def close(self):
            closed.append(True)

    def handler(request):
        requests.append(request)
        return httpx.Response(200, stream=Stream())

    with public_client(handler) as client:
        assert hasattr(client, 'fetch_prefix')
        result = client.fetch_prefix('https://data.example/data.csv')
    assert len(result.body) == 65536
    assert result.truncated is True
    assert len(chunks) == 16
    assert closed
    assert requests[0].headers['range'] == 'bytes=0-65535'
    assert requests[0].extensions['timeout']['read'] <= 5
    assert 'authorization' not in requests[0].headers


@pytest.mark.parametrize('headers', [
    {'Content-Range': 'bytes 4-8/20'},
    {'Content-Range': 'bytes 0-8/8'},
    {'Content-Range': 'garbage'},
    {},
])
def test_prefix_rejects_nonprefix_or_invalid_partial_ranges(headers):
    with public_client(lambda r: httpx.Response(206, headers=headers, content=b'a,b\n1,2\n')) as client:
        assert hasattr(client, 'fetch_prefix')
        with pytest.raises(RequestFailure) as caught:
            client.fetch_prefix('https://data.example/data.csv')
    assert caught.value.status == 'invalid_response'


def test_prefix_accepts_zero_range_and_records_remaining_file():
    with public_client(lambda r: httpx.Response(206,
            headers={'Content-Range': 'bytes 0-7/800'}, content=b'a,b\n1,2\n')) as client:
        assert hasattr(client, 'fetch_prefix')
        result = client.fetch_prefix('https://data.example/data.csv')
    assert result.body == b'a,b\n1,2\n'
    assert result.truncated


def test_prefix_blocks_private_redirect_and_mixed_dns_without_following():
    requests = []
    def handler(request):
        requests.append(request)
        return httpx.Response(302, headers={'Location': 'http://127.0.0.1/data.csv'})
    with public_client(handler) as client:
        assert hasattr(client, 'fetch_prefix')
        with pytest.raises(RequestFailure) as caught:
            client.fetch_prefix('https://data.example/data.csv')
    assert caught.value.status == 'blocked'
    assert len(requests) == 1
    with PublicHTTPClient(transport=httpx.MockTransport(handler),
            resolver=lambda h, p: [PUBLIC_IP, '127.0.0.1']) as client:
        with pytest.raises(RequestFailure) as caught:
            client.fetch_prefix('https://data.example/data.csv')
    assert caught.value.status == 'blocked'
    assert len(requests) == 1


def test_prefix_rejects_compression_without_consuming_body():
    with public_client(lambda r: httpx.Response(200,
            headers={'Content-Encoding': 'gzip'}, content=b'pretend')) as client:
        assert hasattr(client, 'fetch_prefix')
        with pytest.raises(RequestFailure) as caught:
            client.fetch_prefix('https://data.example/data.csv')
    assert caught.value.status == 'network_error'


def test_prefix_clears_cookies_on_redirects():
    sent = []
    def handler(request):
        sent.append(request)
        if len(sent) == 1:
            return httpx.Response(302, headers={'Location': '/next.csv', 'Set-Cookie': 'secret=value'})
        return httpx.Response(200, content=b'a,b\n1,2\n')
    with public_client(handler) as client:
        assert hasattr(client, 'fetch_prefix')
        client.fetch_prefix('https://data.example/data.csv')
    assert len(sent) == 2
    assert all('cookie' not in request.headers for request in sent)


def test_prefix_has_own_elapsed_budget_and_preserves_partial_bytes():
    clock = [0.0]
    class SlowStream(httpx.SyncByteStream):
        def __iter__(self):
            for _ in range(20):
                clock[0] += 2
                yield b'a,b\n'
    with patch('relink.network.monotonic', side_effect=lambda: clock[0]):
        with public_client(lambda r: httpx.Response(200, stream=SlowStream()), total_timeout=100) as client:
            assert hasattr(client, 'fetch_prefix')
            with pytest.raises(RequestFailure) as caught:
                client.fetch_prefix('https://data.example/data.csv')
    assert caught.value.status == 'timeout'
    assert clock[0] <= 12
    assert caught.value.body == b'a,b\n' * 4


def preview(candidate, handler):
    assert importlib.util.find_spec('relink.dataset_preview') is not None
    from relink.dataset_preview import preview_candidate
    with public_client(handler) as client:
        return preview_candidate(candidate, client=client)


def test_preview_reads_only_header_and_three_logical_rows_with_bom():
    result = preview(Candidate(url='https://data.example/data.csv'), lambda r: httpx.Response(
        200, headers={'Content-Type': 'text/csv'},
        content=b'\xef\xbb\xbfname,value\r\n"two\nlines",1\r\nsecond,2\r\nthird,3\r\n"malformed,tail'))
    assert result.status == 'sampled'
    assert result.headers == ('name', 'value')
    assert result.rows == (('two\nlines', '1'), ('second', '2'), ('third', '3'))
    assert result.truncated
    assert result.url == 'https://data.example/data.csv'
    assert result.bytes_read > 0 and result.retrieved_at
    assert 'unverified' in result.detail.lower()
    assert result.response_metadata['http_status'] == 200


def test_preview_uses_actual_datacite_content_url_and_tsv_delimiter():
    result = preview(Candidate(url='https://repository.example/landing', provenance=(CandidateProvenance(
        source='datacite', metadata={'contentUrl': ['https://data.example/data.tsv?download=yes']}),)),
        lambda r: httpx.Response(200, content=b'name\tvalue\nalpha\t10\n'))
    assert result.status == 'sampled'
    assert result.rows == (('alpha', '10'),)
    assert result.url == 'https://data.example/data.tsv?download=yes'


@pytest.mark.parametrize('candidate', [
    Candidate(url='https://data.example/landing'),
    Candidate(url='https://data.example/data.zip'),
    Candidate(url='https://data.example/landing', filenames=('guessed.csv',)),
    Candidate(provenance=(CandidateProvenance(source='other', metadata={'contentUrl': 'https://data.example/data.csv'}),)),
])
def test_no_direct_csv_url_skips_network(candidate):
    def forbidden(request):
        pytest.fail('Metadata-only candidates must not fetch any URL.')
    result = preview(candidate, forbidden)
    assert result.status == 'metadata_only'
    assert not result.headers and not result.rows
    assert result.bytes_read == 0


def test_preview_never_tries_second_advertised_url_after_failure():
    seen = []
    def handler(request):
        seen.append(request.url.path)
        return httpx.Response(404)
    result = preview(Candidate(url='https://data.example/a.csv', archived_url='https://data.example/b.csv'), handler)
    assert result.status == 'not_found'
    assert seen == ['/a.csv']


@pytest.mark.parametrize('body,content_type', [
    (b'<html><body>Access denied, retry</body></html>', 'text/html'),
    (b'<html><body>Access denied, retry</body></html>', 'text/csv'),
    (b'PK\x03\x04\x00abc', 'application/octet-stream'),
    (b'a,b\n"unclosed,2', 'text/csv'),
    (b'a,b\n1,2,3\n', 'text/csv'),
    (b'just ordinary text without columns', 'text/plain'),
    (b'a,b\n1,\xff\n', 'text/csv'),
    (b'a,b\nabc"bad,2\n', 'text/csv'),
])
def test_preview_rejects_html_binary_malformed_and_non_csv(body, content_type):
    result = preview(Candidate(url='https://data.example/data.csv'), lambda r: httpx.Response(
        200, headers={'Content-Type': content_type}, content=body))
    assert result.status == 'invalid_response'
    assert not result.rows
    assert result.bytes_read == len(body)
    assert result.url and result.retrieved_at


def test_truncated_quoted_record_and_incomplete_utf8_never_become_rows():
    body = b'a,b\n1,2\n3,"cut\nrecord' + b'x' * 65514 + b'\xc3\xa9'
    assert len(body) >= 65536
    result = preview(Candidate(url='https://data.example/data.csv'), lambda r: httpx.Response(
        200, content=body))
    assert result.status == 'sampled'
    assert result.headers == ('a', 'b')
    assert result.rows == (('1', '2'),)
    assert result.bytes_read == 65536
    assert result.truncated


def test_truncated_header_must_be_complete():
    result = preview(Candidate(url='https://data.example/data.csv'), lambda r: httpx.Response(
        200, content=b'header,' + b'x' * 65536))
    assert result.status == 'invalid_response'
    assert not result.headers and not result.rows
    assert result.bytes_read == 65536


def test_columns_and_cells_are_bounded_and_reported():
    header = ','.join('column' + str(i) for i in range(40))
    row = ','.join('x' * 300 for _ in range(40))
    result = preview(Candidate(url='https://data.example/data.csv'), lambda r: httpx.Response(
        200, content=(header + '\n' + row + '\n').encode()))
    assert result.status == 'sampled'
    assert len(result.headers) == 32
    assert len(result.rows[0]) == 32
    assert len(result.rows[0][0]) == 240
    assert result.truncated
    assert '32' in result.detail and '240' in result.detail and '3' in result.detail


@pytest.mark.parametrize('code,status', [(429, 'rate_limited'), (404, 'not_found'),
                                        (403, 'blocked'), (500, 'error')])
def test_preview_preserves_http_failure_states(code, status):
    result = preview(Candidate(url='https://data.example/data.csv'), lambda r: httpx.Response(
        code, headers={'Retry-After': '45'}))
    assert result.status == status
    assert result.response_metadata['http_status'] == code
    assert result.response_metadata['retry_after'] == '45'
    assert result.retrieved_at and not result.rows


def test_preview_preserves_partial_source_and_byte_count_on_timeout():
    class Interrupted(httpx.SyncByteStream):
        def __iter__(self):
            yield b'a,b\n1,2\ncut'
            raise httpx.ReadTimeout('interrupted')
    result = preview(Candidate(url='https://data.example/data.csv'), lambda r: httpx.Response(
        200, stream=Interrupted()))
    assert result.status == 'timeout'
    assert result.rows == (('1', '2'),)
    assert result.bytes_read == 11
    assert result.truncated
    assert result.retrieved_at and result.url


def test_preview_unsafe_direct_url_reports_blocked_without_request():
    def forbidden(request):
        pytest.fail('Unsafe URL reached transport.')
    result = preview(Candidate(url='https://127.0.0.1/data.csv'), forbidden)
    assert result.status == 'blocked'
    assert not result.rows


def test_prefix_counts_excess_chunk_as_truncated_even_with_false_length():
    class Oversized(httpx.SyncByteStream):
        def __iter__(self):
            yield b'x' * 4
            yield b'x' * 8
    with public_client(lambda r: httpx.Response(200, headers={'Content-Length': '8'}, stream=Oversized())) as client:
        result = client.fetch_prefix('https://data.example/data.csv', max_bytes=8)
    assert result.body == b'x' * 8
    assert result.truncated


def test_prefix_rejects_unbounded_content_range_instead_of_raising_value_error():
    with public_client(lambda r: httpx.Response(206,
            headers={'Content-Range': 'bytes 0-7/' + '9' * 5000}, content=b'a,b\n1,2\n')) as client:
        with pytest.raises(RequestFailure) as caught:
            client.fetch_prefix('https://data.example/data.csv')
    assert caught.value.status == 'invalid_response'


def test_prefix_rejects_bytes_beyond_advertised_partial_range_even_at_cap():
    class Oversized(httpx.SyncByteStream):
        def __iter__(self):
            yield b'x' * 9
    with public_client(lambda r: httpx.Response(206,
            headers={'Content-Range': 'bytes 0-7/8'}, stream=Oversized())) as client:
        with pytest.raises(RequestFailure) as caught:
            client.fetch_prefix('https://data.example/data.csv', max_bytes=8)
    assert caught.value.status == 'invalid_response'


def test_header_only_complete_prefix_is_preserved_but_no_partial_row_is_used():
    result = preview(Candidate(url='https://data.example/data.csv'), lambda r: httpx.Response(
        206, headers={'Content-Range': 'bytes 0-5/200'}, content=b'a,b\n1,'))
    assert result.status == 'sampled'
    assert result.headers == ('a', 'b')
    assert not result.rows
    assert result.truncated and result.bytes_read == 6


def test_complete_final_row_without_newline_is_allowed_only_at_resource_end():
    result = preview(Candidate(url='https://data.example/data.csv'), lambda r: httpx.Response(
        200, content=b'a,b\n1,2'))
    assert result.rows == (('1', '2'),)
    assert result.truncated is False


def test_datacite_advertised_content_url_string_and_archive_direct_url_are_supported():
    for candidate in (
        Candidate(provenance=(CandidateProvenance('datacite', metadata={'contentUrl': 'https://data.example/raw.csv'}),)),
        Candidate(archived_url='https://archive.example/path/raw.csv'),
    ):
        result = preview(candidate, lambda r: httpx.Response(200, content=b'a,b\n1,2\n'))
        assert result.status == 'sampled'
        assert result.rows == (('1', '2'),)
