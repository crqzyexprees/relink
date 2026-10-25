"""Auth configuration diagnostics use fixture secrets and never make requests."""
import os
from unittest.mock import patch

from tests.test_app import AppTestBase
from tests.test_history_isolation import User


def fixture_auth():
    return {
        'redirect_uri': 'http://localhost:8501/oauth2callback',
        'cookie_secret': 'fixture-cookie-secret-' * 3,
        'client_id': 'fixture-client-id',
        'client_secret': 'private-fixture-client-secret',
        'server_metadata_url': 'https://identity.example/.well-known/openid-configuration',
    }


class AuthConfigurationTests(AppTestBase):
    def setUp(self):
        super().setUp()
        mode = patch.dict(os.environ, {'RELINK_HISTORY_MODE': 'oidc'})
        mode.start()
        self.addCleanup(mode.stop)
        user = patch('streamlit.user', User())
        user.start()
        self.addCleanup(user.stop)

    def test_missing_fields_are_named_without_inventing_a_login_button(self):
        self.app.run()
        text = '\n'.join(c.value for c in self.app.caption)
        for field in fixture_auth():
            self.assertIn('auth.' + field, text)
        self.assertFalse(any(b.key == 'history_login' for b in self.app.button))

    def test_short_cookie_explains_minimum_and_never_displays_secrets(self):
        auth = fixture_auth()
        auth['cookie_secret'] = 'private-short-cookie'
        self.app.secrets['auth'] = auth
        self.app.run()
        text = '\n'.join(c.value for c in self.app.caption)
        self.assertIn('auth.cookie_secret', text)
        self.assertIn('32 characters', text)
        for value in auth.values():
            self.assertNotIn(value, text)
        self.assertFalse(any(b.key == 'history_login' for b in self.app.button))

    def test_named_provider_config_explains_default_auth_table(self):
        auth = fixture_auth()
        self.app.secrets['auth'] = {
            'redirect_uri': auth['redirect_uri'], 'cookie_secret': auth['cookie_secret'],
            'auth0': {k: v for k, v in auth.items() if k not in ('redirect_uri', 'cookie_secret')},
        }
        self.app.run()
        text = '\n'.join(c.value for c in self.app.caption)
        self.assertIn('directly under [auth]', text)
        self.assertNotIn(auth['client_secret'], text)
        self.assertFalse(any(b.key == 'history_login' for b in self.app.button))

    def test_valid_configuration_offers_native_login_without_automatic_requests(self):
        self.app.secrets['auth'] = fixture_auth()
        with patch('streamlit.login') as login:
            self.app.run()
        self.assertTrue(any(b.key == 'history_login' for b in self.app.button))
        self.assertFalse(login.called)
        self.assertFalse(any(e.label == 'Sign-in setup details' for e in self.app.expander))

    def test_disabled_history_points_to_the_top_level_setting(self):
        self.app.secrets['auth'] = fixture_auth()
        with patch.dict(os.environ, {'RELINK_HISTORY_ENABLED': '0'}):
            self.app.run()
        text = '\n'.join(c.value for c in self.app.caption)
        self.assertIn('RELINK_HISTORY_ENABLED = "1"', text)
        self.assertIn('above [auth]', text)
        self.assertTrue(any(b.key == 'history_login' for b in self.app.button))
