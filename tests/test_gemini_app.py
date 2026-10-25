"""Gemini is automatic on explicit paper actions; all external HTTP is mocked."""
import json
import os
from unittest.mock import patch

import httpx

from relink.gemini_config import GeminiSettings
from relink.history import HistoryStore, restore_snapshot
from relink.network import PublicHTTPClient
from relink.papers import lookup_paper_datasets, lookup_uploaded_datasets
from tests.pdf_fixtures import make_pdf
from tests.test_app import AppTestBase
from tests.test_datacite import record
from tests.test_gemini import KEY, mention, response
from tests.test_paper_app import paper_result
from tests.test_dataset_ai import ai_response


class GeminiAppTests(AppTestBase):
    def setUp(self):
        super().setUp()
        self.calls = []
        def handler(request):
            self.calls.append(request)
            host = request.headers['host']
            if host == 'generativelanguage.googleapis.com':
                data = json.loads(json.loads(request.content)['contents'][0]['parts'][0]['text'])
                if 'datasets' in data: return ai_response(request)
                return httpx.Response(200, json=response([mention(quote='We use the SQuAD 1.1 dataset.')] ))
            if host == 'api.datacite.org':
                self.assertNotIn('x-goog-api-key', request.headers)
                return httpx.Response(200, json={'data': [record(titles=[{'title': 'SQuAD'}])], 'meta': {'total': 1}})
            return httpx.Response(200, content=make_pdf('We use the SQuAD 1.1 dataset.'))
        self.client = PublicHTTPClient(transport=httpx.MockTransport(handler), resolver=lambda h, p: ['93.184.215.14'])
        self.addCleanup(self.client.close)
        settings = patch('relink.gemini_config.load_gemini_settings', return_value=GeminiSettings(KEY))
        settings.start()
        self.addCleanup(settings.stop)

    def test_selected_paper_find_automatically_identifies_and_searches_names(self):
        with patch('relink.paper_ui.search_papers', return_value=paper_result()), patch(
            'relink.paper_ui.lookup_paper_datasets', side_effect=lambda paper, **kw:
                lookup_paper_datasets(paper, client=self.client, **kw)):
            self.app.run()
            self.app.text_area(key='paper_topic').set_value('forest climate').run()
            self.app.button(key='find_papers').click().run()
            self.assertEqual(len(self.calls), 0)
            self.app.button(key='lookup_paper_datasets').click().run()
            self.assertEqual(len(self.app.exception), 0)
            self.assertEqual(sum(r.method == 'POST' for r in self.calls), 2)
            self.assertTrue(any('We use the SQuAD 1.1 dataset.' in item.value for item in self.app.text))
            self.assertTrue(any('SQuAD' in item.value for item in self.app.text))
            self.app.run()
            self.assertEqual(sum(r.method == 'POST' for r in self.calls), 2)
        entries = HistoryStore(os.environ['RELINK_HISTORY_PATH']).list()
        lookup = restore_snapshot(entries[0])
        self.assertEqual(lookup.identification.mentions[0].name, 'SQuAD')
        stored = open(os.environ['RELINK_HISTORY_PATH']).read()
        self.assertNotIn(KEY, stored)
        self.assertNotIn('"pages"', stored)

    def test_link_free_uploaded_pdf_has_real_find_action_and_no_request_on_upload(self):
        with patch('relink.ui.lookup_uploaded_datasets', side_effect=lambda extraction, **kw:
            lookup_uploaded_datasets(extraction, client=self.client, **kw)):
            self.app.run()
            self.app.radio[0].set_value('Analyze PDF').run()
            self.app.file_uploader[0].set_value(('paper.pdf', make_pdf('We use the SQuAD 1.1 dataset.'), 'application/pdf')).run()
            self.assertFalse(self.recover_button().disabled)
            self.assertFalse(self.calls)
            self.recover_button().click().run()
            self.assertEqual(len(self.app.exception), 0)
            self.assertTrue(any('SQuAD' in item.value for item in self.app.text))
            self.app.run()
            self.assertEqual(sum(r.method == 'POST' for r in self.calls), 2)
            self.assertTrue(self.app.button(key='history_rerun').disabled)
        entry = HistoryStore(os.environ['RELINK_HISTORY_PATH']).list()[0]
        self.assertEqual(restore_snapshot(entry).identification.status, 'found')
