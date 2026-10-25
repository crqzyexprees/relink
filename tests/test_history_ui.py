"""History survives fresh AppTest sessions without invoking services on view."""
import os
from dataclasses import replace
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from relink.history import HistoryStore
from tests.test_app import APP, AppTestBase, mock_report
from tests.test_paper_app import paper_result


class HistoryUITests(AppTestBase):
    def test_recovery_saved_once_and_fresh_session_can_view_without_requests(self):
        with patch('relink.ui.run_recovery', return_value=mock_report()) as run:
            self.app.run()
            self.app.text_input(key='original_url').set_value('https://example.org/data.csv').run()
            self.recover_button().click().run()
            store = HistoryStore(os.environ['RELINK_HISTORY_PATH'])
            self.assertEqual(len(store.list()), 1)
            self.app.run()
            self.assertEqual(len(store.list()), 1)
            self.assertEqual(run.call_count, 1)
        reopened = AppTest.from_file(str(APP), default_timeout=10)
        with patch('relink.history_ui.run_recovery', side_effect=AssertionError('View made a request')):
            reopened.run()
            reopened.button(key='history_view').click().run()
        self.assertEqual(len(reopened.exception), 0)
        self.assertTrue(any('Saved results' in item.value for item in reopened.warning))
        self.assertTrue(any(item.value == 'Mocked research measurements' for item in reopened.text))

    def test_paper_history_explicit_search_again_adds_new_dated_entry(self):
        with patch('relink.paper_ui.search_papers', return_value=paper_result()) as search:
            self.app.run()
            self.app.text_area(key='paper_topic').set_value('forest climate').run()
            self.app.button(key='find_papers').click().run()
        store = HistoryStore(os.environ['RELINK_HISTORY_PATH'])
        self.assertEqual(len(store.list()), 1)
        with patch('relink.history_ui.search_papers', return_value=paper_result()) as rerun:
            self.app.button(key='history_rerun').click().run()
        self.assertEqual(rerun.call_count, 1)
        self.assertEqual(rerun.call_args.args[0], 'forest climate')
        self.assertEqual(len(store.list()), 2)
        self.assertNotEqual(store.list()[0].id, store.list()[1].id)

    def test_delete_clear_and_disabled_history(self):
        store = HistoryStore(os.environ['RELINK_HISTORY_PATH'])
        store.add('recovery', 'first', mock_report())
        store.add('recovery', 'second', mock_report())
        self.app.run()
        self.app.button(key='history_delete').click().run()
        self.assertEqual(len(store.list()), 1)
        self.app.button(key='history_clear').click().run()
        self.assertEqual(store.list(), [])
        with patch.dict(os.environ, {'RELINK_HISTORY_ENABLED': '0'}), patch(
            'relink.ui.run_recovery', return_value=mock_report()):
            self.app.text_input(key='original_url').set_value('https://example.org/data.csv').run()
            self.recover_button().click().run()
        self.assertEqual(store.list(), [])

    def test_history_write_failure_does_not_discard_search_results(self):
        with patch('relink.ui.run_recovery', return_value=mock_report()), patch(
            'relink.history.os.replace', side_effect=OSError('mock disk failure')):
            self.app.run()
            self.app.text_input(key='original_url').set_value('https://example.org/data.csv').run()
            self.recover_button().click().run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertIn('report', self.app.session_state)
        self.assertTrue(any('history could not be saved' in item.value for item in self.app.warning))

    def test_rerun_storage_failure_still_shows_new_results(self):
        store = HistoryStore(os.environ['RELINK_HISTORY_PATH'])
        store.add('recovery', 'saved URL', mock_report())
        self.app.run()
        with patch('relink.history_ui.run_recovery', return_value=mock_report()), patch(
            'relink.history.os.replace', side_effect=OSError('mock disk failure')):
            self.app.button(key='history_rerun').click().run()
        self.assertTrue(any(item.value == 'Mocked research measurements' for item in self.app.text))
        self.assertTrue(any('not saved' in item.value for item in self.app.warning))
        self.assertEqual(len(store.list()), 1)

    def test_oversized_rerun_result_stays_visible_without_being_persisted(self):
        store = HistoryStore(os.environ['RELINK_HISTORY_PATH'])
        store.add('recovery', 'saved URL', mock_report())
        self.app.run()
        huge = replace(mock_report(), input_context={'note': 'x' * (2 * 1024 * 1024)})
        with patch('relink.history_ui.run_recovery', return_value=huge):
            self.app.button(key='history_rerun').click().run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertTrue(any(item.value == 'Mocked research measurements' for item in self.app.text))
        self.assertTrue(any('not saved' in item.value for item in self.app.warning))
        self.assertEqual(len(store.list()), 1)
