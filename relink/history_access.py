"""Trusted identity → private history namespace; no browser-supplied storage paths."""
from dataclasses import dataclass
from collections.abc import Mapping
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import time

import streamlit as st

from relink.history import HistoryError, HistoryStore


@dataclass(frozen=True)
class HistoryAccess:
    mode: str
    enabled: bool
    namespace: str = ''
    detail: str = ''

    @property
    def scope(self):
        return f'{self.mode}:{self.namespace or "guest"}'


class IdentityChanged(HistoryError):
    """Discard an action started under another identity instead of publishing it."""


def ensure_action_scope(expected_scope):
    if current_access().scope != expected_scope:
        raise IdentityChanged('Sign-in changed during this action; its result was discarded.')


def rerun_if_identity_changed(expected_scope):
    if current_access().scope != expected_scope:
        st.rerun(scope='app')


def resolve_access(mode, enabled, claims, *, now=None) -> HistoryAccess:
    """Claims must come from Streamlit's validated OIDC identity, never input."""
    if mode not in ('oidc', 'local'):
        return HistoryAccess('invalid', False, detail='History configuration is invalid; saving is disabled.')
    if mode == 'local':
        return HistoryAccess(mode, bool(enabled), 'local', 'Shared history for this trusted local workspace.' if enabled else
                             'Persistent history is disabled for this deployment.')
    namespace = ''
    if isinstance(claims, dict) and claims.get('is_logged_in') is True:
        issuer, subject, expiry = (claims.get(key) for key in ('iss', 'sub', 'exp'))
        valid_strings = all(isinstance(value, str) and value.strip() and len(value) <= limit and
                            not any(ord(char) < 32 or ord(char) == 127 or 0xd800 <= ord(char) <= 0xdfff for char in value)
                            for value, limit in ((issuer, 2048), (subject, 512)))
        valid_expiry = (type(expiry) in (int, float) and 0 < expiry <= 253402300799 and math.isfinite(expiry) and
                        expiry > (time.time() if now is None else now))
        if valid_strings and valid_expiry:
            identity = json.dumps([issuer, subject], ensure_ascii=False, separators=(',', ':'))
            namespace = hashlib.sha256(identity.encode('utf-8')).hexdigest()
    detail = ('Persistent history is disabled for this deployment.' if not enabled else
              'Private history for your signed-in account.' if namespace else
              'Sign in to save and reopen your private search history.')
    return HistoryAccess(mode, bool(enabled and namespace), namespace, detail)


def history_enabled() -> bool:
    return os.environ.get('RELINK_HISTORY_ENABLED', '1').strip().lower() not in ('0', 'false', 'off', 'no')


def current_access() -> HistoryAccess:
    mode = os.environ.get('RELINK_HISTORY_MODE', 'oidc').strip().lower()
    enabled = history_enabled()
    try:
        claims = st.user.to_dict() if mode == 'oidc' else {}
    except (AttributeError, KeyError, RuntimeError):
        claims = {}
    return resolve_access(mode, enabled, claims)


def store_for_access(access: HistoryAccess) -> HistoryStore:
    if not access.enabled:
        raise HistoryError('Private history requires a current authorized identity.')
    default = Path(__file__).resolve().parents[1] / '.relink' / 'history.json'
    base = Path(os.environ.get('RELINK_HISTORY_PATH') or default)
    if access.mode == 'local' and access.namespace == 'local':
        return HistoryStore(base)
    if access.mode != 'oidc' or not re.fullmatch('[0-9a-f]{64}', access.namespace):
        raise HistoryError('History identity is invalid.')
    return HistoryStore(base.parent / (base.stem + '-users') / (access.namespace + '.json'))


def authorized_store(expected_scope: str) -> HistoryStore:
    access = current_access()
    if not access.enabled or access.scope != expected_scope:
        raise HistoryError('Your sign-in changed or expired. Reopen history after signing in.')
    return store_for_access(access)


def sync_session_scope(access: HistoryAccess):
    """Run before widgets; discard previous identity's uploads/forms/results."""
    previous = st.session_state.get('_history_identity_scope')
    if previous is not None and previous != access.scope:
        st.session_state.clear()
    st.session_state['_history_identity_scope'] = access.scope


def login_configuration_issues() -> tuple[str, ...]:
    """Return only application-owned messages/field names, never secret values."""
    issues = []
    if importlib.util.find_spec('authlib') is None:
        issues.append('Authentication dependency missing: install streamlit[auth] and reboot the app.')
    try:
        auth = st.secrets.get('auth', {})
        if not isinstance(auth, Mapping):
            return tuple(issues + ['The [auth] setting must be a TOML table.'])
        required = ('redirect_uri', 'cookie_secret', 'client_id', 'client_secret', 'server_metadata_url')
        missing = [name for name in required if not isinstance(auth.get(name), str) or not auth[name].strip()]
        issues.extend(f'Set auth.{name} to a nonempty string.' for name in missing)
        if 'cookie_secret' not in missing and len(auth['cookie_secret']) < 32:
            issues.append('auth.cookie_secret must contain at least 32 characters; generate a random secret.')
        if missing and any(isinstance(value, Mapping) for name, value in auth.items() if name != 'client_kwargs'):
            issues.append('Put client_id, client_secret and server_metadata_url directly under [auth]; '
                          'ReLink uses the default provider.')
    except (FileNotFoundError, KeyError, ValueError, TypeError, AttributeError):
        issues.append('Authentication secrets could not be read. Check the deployed app Secrets settings and reboot.')
    return tuple(issues)


def login_configured() -> bool:
    """Support the native single-provider [auth] config without exposing secrets."""
    return not login_configuration_issues()
