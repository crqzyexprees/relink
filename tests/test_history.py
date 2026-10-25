"""Persistent history uses temporary files and mocked/local-only result data."""
from dataclasses import asdict, replace
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from relink.history import HistoryError, HistoryStore, restore_snapshot
from relink.paper_models import PaperDatasetLookup
from relink.models import SearchResult
from tests.test_app import mock_report
from tests.test_paper_app import paper_result


class HistoryTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.path = Path(folder.name) / 'history.json'
        self.store = HistoryStore(self.path)

    def test_round_trip_new_instance_and_new_process_keep_dated_results(self):
        entry = self.store.add('recovery', 'https://example.org/data.csv', mock_report())
        restored = HistoryStore(self.path).list()[0]
        self.assertEqual(restored, entry)
        self.assertEqual(restore_snapshot(restored), mock_report())
        completed = subprocess.run([sys.executable, '-c',
            'from relink.history import HistoryStore; import sys; print(HistoryStore(sys.argv[1]).list()[0].id)',
            str(self.path)], capture_output=True, text=True, check=True)
        self.assertEqual(completed.stdout.strip(), entry.id)
        self.assertTrue(entry.created_at.endswith('+00:00'))
        self.assertEqual(os.stat(self.path).st_mode & 0o777, 0o600)

    def test_all_snapshot_types_and_failure_status_survive(self):
        search = paper_result()
        self.store.add('papers', 'forest climate', search, request={'topic': 'forest climate'})
        lookup = PaperDatasetLookup('https://openalex.org/W1', SearchResult('timeout', 'datacite'), pdf_status='unavailable')
        self.store.add('paper_datasets', 'Forest paper', lookup,
                       request={'paper': asdict(search.papers[0].paper)})
        self.store.add('recovery', 'failed URL', mock_report(status='error'))
        entries = self.store.list()
        self.assertEqual(restore_snapshot(entries[0]).discovery.status, 'error')
        self.assertEqual(restore_snapshot(entries[1]).datasets.status, 'timeout')
        self.assertEqual(restore_snapshot(entries[2]), search)

    def test_retention_deletion_clear_and_missing_file(self):
        self.assertEqual(self.store.list(), [])
        store = HistoryStore(self.path, max_entries=2)
        first = store.add('recovery', 'first', mock_report())
        second = store.add('recovery', 'second', mock_report())
        third = store.add('recovery', 'third', mock_report())
        self.assertEqual([e.id for e in store.list()], [third.id, second.id])
        store.delete(second.id)
        self.assertEqual([e.id for e in store.list()], [third.id])
        store.clear()
        self.assertEqual(store.list(), [])

    def test_corrupt_or_incompatible_file_is_not_silently_overwritten(self):
        for data in (b'{bad', b'{"version":999,"entries":[]}', b'[' * 10000 + b']' * 10000):
            self.path.write_bytes(data)
            with self.subTest(data=data[:20]), self.assertRaises(HistoryError):
                self.store.add('recovery', 'new', mock_report())
            self.assertEqual(self.path.read_bytes(), data)

    def test_storage_failure_preserves_previous_file_and_no_pdf_bytes_accepted(self):
        self.store.add('recovery', 'before', mock_report())
        before = self.path.read_bytes()
        with patch('relink.history.os.replace', side_effect=OSError('disk failure')):
            with self.assertRaises(HistoryError): self.store.add('recovery', 'after', mock_report())
        self.assertEqual(self.path.read_bytes(), before)
        with self.assertRaises(HistoryError):
            self.store.add('recovery', 'bad', mock_report(), request={'pdf_bytes': b'%PDF-test'})

    def test_invalid_snapshot_and_oversized_files_are_rejected(self):
        entry = self.store.add('recovery', 'before', mock_report())
        data = json.loads(self.path.read_text())
        data['entries'][0]['snapshot']['query']['original_url'] = 'http://127.0.0.1/secret'
        self.path.write_text(json.dumps(data))
        with self.assertRaises(HistoryError): self.store.list()
        self.path.write_bytes(b' ' * (10 * 1024 * 1024 + 1))
        with self.assertRaises(HistoryError): self.store.list()

    def test_concurrent_threads_do_not_lose_local_workspace_entries(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            entries = list(pool.map(lambda index: HistoryStore(self.path).add(
                'recovery', str(index), mock_report()), range(8)))
        self.assertEqual({entry.id for entry in self.store.list()}, {entry.id for entry in entries})

    def test_invalid_requests_and_large_entries_are_rejected_before_writing(self):
        self.store.add('recovery', 'first', mock_report())
        before = self.path.read_bytes()
        with self.assertRaises(HistoryError): self.store.add('papers', 'bad request', paper_result())
        report = mock_report()
        report = replace(report, input_context={'note': 'x' * (2 * 1024 * 1024)})
        with self.assertRaises(HistoryError): self.store.add('recovery', 'oversized', report)
        self.assertEqual(self.path.read_bytes(), before)
