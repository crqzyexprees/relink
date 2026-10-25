"""Privacy boundary tests. Identity-provider claims are mocked; storage/UI are real."""
import json
from dataclasses import replace
import os
from pathlib import Path
import time
import unittest
from unittest.mock import patch
from base64 import b64decode
from html.parser import HTMLParser

from streamlit.testing.v1 import AppTest

from relink.history import HistoryError, HistoryStore
from tests.test_app import APP, AppTestBase, mock_report


def claims(subject='alice', issuer='https://identity.example', **changes):
    return {'is_logged_in': True, 'iss': issuer, 'sub': subject,
            'exp': time.time() + 3600, **changes}


class User(dict):
    def to_dict(self):
        return dict(self)


class ExportParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.exports = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == 'button' and 'data-payload' in attributes:
            self.exports.append(json.loads(b64decode(attributes['data-payload'])))


class HistoryIsolationTests(AppTestBase):
    def test_accounts_have_independent_crud_and_legacy_file_is_not_assigned(self):
        from relink.history_access import resolve_access, store_for_access
        legacy = HistoryStore(os.environ['RELINK_HISTORY_PATH'])
        legacy.add('recovery', 'Old shared entry', mock_report())
        a = store_for_access(resolve_access('oidc', True, claims()))
        b = store_for_access(resolve_access('oidc', True, claims('bob')))
        first = a.add('recovery', 'Alice private', mock_report())
        second = b.add('recovery', 'Bob private', mock_report())
        self.assertEqual([e.label for e in a.list()], ['Alice private'])
        self.assertEqual([e.label for e in b.list()], ['Bob private'])
        self.assertNotEqual(a.path, b.path)
        self.assertNotIn('alice', str(a.path))
        self.assertNotIn('identity.example', str(a.path))
        a.delete(second.id)
        self.assertEqual([e.id for e in b.list()], [second.id])
        a.delete(first.id)
        a.clear()
        self.assertEqual(a.list(), [])
        self.assertEqual(len(b.list()), 1)
        self.assertEqual([e.label for e in legacy.list()], ['Old shared entry'])

    def test_same_identity_reopens_but_same_email_or_subject_other_issuer_does_not(self):
        from relink.history_access import resolve_access, store_for_access
        a = store_for_access(resolve_access('oidc', True, claims(email='shared@example.org')))
        a.add('recovery', 'Durable', mock_report())
        same = store_for_access(resolve_access('oidc', True, claims(email='changed@example.org')))
        other_subject = store_for_access(resolve_access('oidc', True, claims('bob', email='shared@example.org')))
        other_issuer = store_for_access(resolve_access('oidc', True, claims(issuer='https://other.example')))
        self.assertEqual([e.label for e in same.list()], ['Durable'])
        self.assertEqual(other_subject.list(), [])
        self.assertEqual(other_issuer.list(), [])

    def test_anonymous_invalid_expired_and_disabled_identities_fail_closed(self):
        from relink.history_access import resolve_access, store_for_access
        invalid = [{}, claims(is_logged_in=False), claims(is_logged_in='true'),
                   claims(sub=''), claims(iss=''),
                   claims(sub='bad\nclaim'), claims(exp=0), claims(exp=True),
                   claims(exp=float('nan')), claims(exp=float('inf')), claims(exp='9999999999')]
        invalid.extend([claims(exp=10**1000), claims(sub='\ud800')])
        without_exp = claims()
        del without_exp['exp']
        invalid.append(without_exp)
        for identity in invalid:
            with self.subTest(identity=identity):
                access = resolve_access('oidc', True, identity)
                with self.assertRaises(HistoryError): store_for_access(access)
        for mode, enabled in [('garbage', True), ('oidc', False), ('local', False)]:
            with self.subTest(mode=mode, enabled=enabled):
                with self.assertRaises(HistoryError):
                    store_for_access(resolve_access(mode, enabled, claims()))

    def test_explicit_local_mode_retains_old_store_only_when_enabled(self):
        from relink.history_access import resolve_access, store_for_access
        local = store_for_access(resolve_access('local', True, {}))
        self.assertEqual(local.path, Path(os.environ['RELINK_HISTORY_PATH']))

    def test_subject_is_hashed_never_interpreted_as_a_path(self):
        from relink.history_access import resolve_access, store_for_access
        store = store_for_access(resolve_access('oidc', True, claims('../../outside')))
        self.assertEqual(store.path.parent, Path(os.environ['RELINK_HISTORY_PATH']).parent / 'history-users')
        self.assertEqual(len(store.path.stem), 64)
        self.assertNotIn('outside', str(store.path))


class HistoryIsolationUITests(AppTestBase):
    def setUp(self):
        super().setUp()
        mode = patch.dict(os.environ, {'RELINK_HISTORY_MODE': 'oidc'})
        mode.start()
        self.addCleanup(mode.stop)
        self.user = User()
        identity = patch('streamlit.user', self.user)
        identity.start()
        self.addCleanup(identity.stop)

    def login(self, subject='alice'):
        self.user.clear()
        self.user.update(claims(subject))

    def save_url(self, url):
        with patch('relink.ui.run_recovery', return_value=mock_report()):
            self.app.run()
            self.app.text_input(key='original_url').set_value(url).run()
            self.recover_button().click().run()
        self.assertEqual(len(self.app.exception), 0)

    def test_guest_cannot_read_or_modify_shared_history_but_can_search(self):
        legacy = HistoryStore(os.environ['RELINK_HISTORY_PATH'])
        legacy.add('recovery', 'Private old shared search', mock_report())
        self.app.run()
        self.assertFalse(any(item.key == 'history_selection' for item in self.app.selectbox))
        self.assertFalse(any(item.key in ('history_clear', 'history_export') for item in self.app.button))
        self.save_url('https://example.org/guest.csv')
        self.assertIn('report', self.app.session_state)
        self.assertEqual([e.label for e in legacy.list()], ['Private old shared search'])

    def test_missing_login_config_has_no_operational_button_and_default_is_private(self):
        from relink.history_access import current_access
        self.app.run()
        self.assertFalse(any(b.key == 'history_login' for b in self.app.button))
        with patch.dict(os.environ):
            os.environ.pop('RELINK_HISTORY_MODE', None)
            self.assertEqual(current_access().mode, 'oidc')
            self.assertFalse(current_access().enabled)

    def test_login_start_failure_is_clear_and_never_renders_credentials(self):
        self.app.secrets['auth'] = {
            'redirect_uri': 'http://localhost:8501/oauth2callback', 'cookie_secret': 'fixture' * 10,
            'client_id': 'fixture-client', 'client_secret': 'private-client-secret',
            'server_metadata_url': 'https://identity.example/.well-known/openid-configuration'}
        self.app.run()
        with patch('streamlit.login', side_effect=ValueError('private-client-secret')):
            self.app.button(key='history_login').click().run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertTrue(self.app.error)
        self.assertFalse(any('private-client-secret' in item.value for item in self.app.error))

    def test_private_export_encodes_remote_markup_as_inert_json_bytes(self):
        from relink.history_access import current_access, store_for_access
        self.login()
        dangerous = '</script><script>alert("remote")</script><img src="https://evil.example/x">'
        store_for_access(current_access()).add('recovery', dangerous, mock_report())
        self.app.run()
        parser = ExportParser()
        for block in self.app.get('html'):
            self.assertNotIn(dangerous, block.proto.body)
            parser.feed(block.proto.body)
        self.assertEqual(parser.exports[0]['entries'][0]['label'], dangerous)
        self.assertFalse(self.app.get('download_button'))

    def test_account_switch_clears_results_and_only_exports_deletes_own_entries(self):
        from relink.history_access import current_access, store_for_access
        self.login()
        self.save_url('https://example.org/alice.csv')
        alice = store_for_access(current_access())
        entry = alice.list()[0]
        self.assertIn('report', self.app.session_state)
        self.login('bob')
        self.app.run()
        self.assertNotIn('report', self.app.session_state)
        self.assertEqual(self.app.text_input(key='original_url').value, '')
        self.assertFalse(any(item.key == 'history_selection' for item in self.app.selectbox))
        self.save_url('https://example.org/bob.csv')
        bob = store_for_access(current_access())
        saved = json.loads(bob.path.read_text())
        self.assertEqual(len(saved['entries']), 1)
        self.assertNotIn('alice.csv', json.dumps(saved))
        # The actual export widget must contain only Bob's current list.
        self.assertFalse(self.app.get('download_button'), 'Private exports must not register global /media URLs')
        parser = ExportParser()
        for block in self.app.get('html'): parser.feed(block.proto.body)
        exported = next(payload for payload in parser.exports if 'entries' in payload)
        self.assertEqual([e['label'] for e in exported['entries']], ['https://example.org/bob.csv'])
        self.app.button(key='history_delete').click().run()
        self.assertEqual(bob.list(), [])
        self.assertEqual([e.id for e in alice.list()], [entry.id])
        self.app.button(key='history_clear').click().run()
        self.assertEqual(len(alice.list()), 1)

    def test_identity_change_during_normal_find_never_saves_or_renders_previous_input(self):
        from relink.history_access import current_access, store_for_access
        self.login()
        alice = store_for_access(current_access())
        self.app.run()
        self.app.text_input(key='original_url').set_value('https://example.org/alice-secret.csv').run()
        def change_user(*args, **kwargs):
            self.login('bob')
            return mock_report()
        with patch('relink.ui.run_recovery', side_effect=change_user):
            self.recover_button().click().run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertNotIn('report', self.app.session_state)
        self.assertEqual(alice.list(), [])
        self.assertEqual(store_for_access(current_access()).list(), [])

    def test_failed_remote_action_also_clears_previous_identity_form_and_error(self):
        self.login()
        self.app.run()
        self.app.text_input(key='original_url').set_value('https://example.org/alice-secret.csv').run()
        def change_user_and_fail(*args, **kwargs):
            self.login('bob')
            raise ValueError('Alice private source error')
        with patch('relink.ui.run_recovery', side_effect=change_user_and_fail):
            self.recover_button().click().run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertEqual(self.app.text_input(key='original_url').value, '')
        self.assertNotIn('recovery_error', self.app.session_state)

    def test_saved_results_survive_fresh_session_and_logout_hides_them(self):
        self.login()
        self.save_url('https://example.org/alice.csv')
        fresh = AppTest.from_file(str(APP), default_timeout=10)
        with patch('relink.history_ui.run_recovery', side_effect=AssertionError('View made a request')):
            fresh.run()
            fresh.button(key='history_view').click().run()
        self.assertEqual(len(fresh.exception), 0)
        self.assertTrue(any(t.value == 'Mocked research measurements' for t in fresh.text))
        self.user.clear()
        fresh.run()
        self.assertFalse(any(item.key == 'history_selection' for item in fresh.selectbox))
        self.assertFalse(any(t.value == 'Mocked research measurements' for t in fresh.text))

    def test_stale_history_handle_is_rejected_before_remote_work(self):
        from relink.history_access import current_access, store_for_access
        from relink.history_ui import _search_again
        self.login()
        access = current_access()
        entry = store_for_access(access).add('recovery', 'Alice', mock_report())
        self.login('bob')
        with patch('relink.history_ui.run_recovery', side_effect=AssertionError('Unauthorized request')):
            with self.assertRaises(HistoryError): _search_again(entry.id, access.scope)

    def test_identity_change_during_remote_rerun_never_saves_into_other_account(self):
        from relink.history_access import current_access, store_for_access
        from relink.history_ui import _search_again
        self.login()
        access = current_access()
        alice = store_for_access(access)
        entry = alice.add('recovery', 'Alice', mock_report())
        def change_user(*args, **kwargs):
            self.login('bob')
            return mock_report()
        with patch('relink.history_ui.run_recovery', side_effect=change_user):
            with self.assertRaises(HistoryError): _search_again(entry.id, access.scope)
        self.assertEqual(len(alice.list()), 1)
        self.assertEqual(store_for_access(current_access()).list(), [])

    def test_expiry_clears_active_results_and_prevents_private_history_reads(self):
        self.login()
        self.save_url('https://example.org/alice.csv')
        self.user['exp'] = 0
        self.app.run()
        self.assertNotIn('report', self.app.session_state)
        self.assertFalse(any(item.key == 'history_selection' for item in self.app.selectbox))

    def test_expiry_inside_dialog_fragment_forces_full_state_reset(self):
        from streamlit.runtime.scriptrunner_utils.script_requests import ScriptRequests
        self.login()
        self.save_url('https://example.org/alice.csv')
        self.app.button(key='history_view').click().run()
        fragment_id = next(iter(self.app._fragment_storage._fragments))
        self.user['exp'] = 0
        original = ScriptRequests.request_rerun
        requests_seen = 0
        def request_fragment(requests, data):
            nonlocal requests_seen
            requests_seen += 1
            if requests_seen <= 2:
                data = replace(data, fragment_id_queue=[fragment_id])
            return original(requests, data)
        with patch.object(ScriptRequests, 'request_rerun', request_fragment):
            self.app.run()
        self.assertEqual(len(self.app.exception), 0)
        self.assertNotIn('report', self.app.session_state)
        self.assertEqual(self.app.text_input(key='original_url').value, '')
