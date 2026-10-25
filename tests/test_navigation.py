"""Compact native navigation and useful interactions, without automatic searches."""
import os
from unittest.mock import patch

from tests.test_app import AppTestBase


class NavigationTests(AppTestBase):
    def test_three_workspaces_place_legal_material_in_its_own_tab(self):
        with patch.dict(os.environ, {'RELINK_SOURCE_URL': 'https://github.com/crqzyexprees/relink'}):
            self.app.run()
        self.assertEqual([tab.label for tab in self.app.tabs], ['Find datasets', 'Find papers', 'License & source'])
        legal = self.app.tabs[2]
        self.assertTrue(any('WITHOUT ANY WARRANTY' in t.value for t in legal.text))
        self.assertTrue(any(link.proto.label == 'Source code' for link in legal.get('link_button')))
        self.assertFalse(any(e.label == 'License and source code' for e in self.app.expander))
        self.assertEqual(self.app.title[0].value, 'ReLink')
        self.assertFalse(any('Follow the signal. Reconnect your research.' in m.value for m in self.app.markdown))

    def test_dataset_example_populates_real_input_without_remote_work(self):
        with patch('relink.ui.run_recovery') as recover, patch('relink.paper_ui.search_papers') as papers:
            self.app.run()
            self.app.button(key='dataset_example_iris').click().run()
            self.assertEqual(self.app.radio(key='input_mode').value, 'Search datasets')
            self.assertEqual(self.app.text_input(key='dataset_topic').value, '10.24432/c56c76')
            self.assertFalse(self.recover_button().disabled)
            self.assertFalse(recover.called)
            self.assertFalse(papers.called)
            self.assertEqual(len(self.app.exception), 0)

    def test_paper_example_populates_topic_and_requires_explicit_find(self):
        with patch('relink.paper_ui.search_papers') as search:
            self.app.run()
            self.app.button(key='paper_example_medical').click().run()
            self.assertTrue(self.app.text_area(key='paper_topic').value.strip())
            self.assertFalse(self.app.button(key='find_papers').disabled)
            self.app.run()
            self.assertFalse(search.called)

    def test_navigation_rerun_preserves_both_workspace_inputs(self):
        with patch('relink.ui.run_recovery') as recover, patch('relink.paper_ui.search_papers') as search:
            self.app.run()
            self.app.text_input(key='original_url').set_value('https://example.org/data.csv').run()
            self.app.text_area(key='paper_topic').set_value('forest measurements').run()
            self.app.run()
            self.assertEqual(self.app.text_input(key='original_url').value, 'https://example.org/data.csv')
            self.assertEqual(self.app.text_area(key='paper_topic').value, 'forest measurements')
            self.assertFalse(recover.called)
            self.assertFalse(search.called)
