# Private history and Streamlit login

ReLink now defaults to private persistent history. Streamlit authenticates users
with OIDC; ReLink separately authorizes every history operation and chooses a
private store from the trusted issuer/subject pair. Guests can run searches but
cannot read or save disk history. Missing/expired/malformed identity never falls
back to shared storage. See [Streamlit authentication](https://docs.streamlit.io/develop/concepts/connections/authentication)
and [st.user](https://docs.streamlit.io/develop/api-reference/user/st.user).

## Configure a real provider

The Gemini API key is separate from OAuth login credentials. Register a web
application in your chosen OIDC provider; ReLink does not create provider accounts
or applications, purchase services, or manage passwords.

1. Install requirements (`streamlit[auth]` includes the supported Authlib integration):
   `.venv/bin/python -m pip install -r requirements.txt`.
2. For Auth0, create a **Regular Web Application**. Register
   `http://localhost:8501/oauth2callback` as its allowed callback URL. Where the
   provider requires an allowed post-logout redirect URL, use that exact URL too.
   Copy the application's client ID/secret and tenant domain privately.
   Google Identity is also supported via an OAuth web client with the same
   registered redirect. Provider setup starts in its admin console; do not use
   fabricated credentials or a Gemini API key for this step.
3. Add the following section to your existing ignored `.streamlit/secrets.toml`.
   Preserve the current top-level Gemini values **above** `[auth]`:

   ```toml
   [auth]
   redirect_uri = "http://localhost:8501/oauth2callback"
   cookie_secret = "YOUR_PRIVATE_RANDOM_SECRET_AT_LEAST_32_BYTES"
   client_id = "YOUR_OIDC_CLIENT_ID"
   client_secret = "YOUR_OIDC_CLIENT_SECRET"
   server_metadata_url = "https://YOUR_AUTH0_DOMAIN/.well-known/openid-configuration"
   ```

   For Google, use
   `https://accounts.google.com/.well-known/openid-configuration` as metadata URL.
   A blank example is in [secrets.example.toml](../.streamlit/secrets.example.toml).
   Generate the cookie secret privately with Python's `secrets.token_urlsafe(32)`;
   never paste it into chat, a commit, screenshot, public report or screen recording.
   No token exposure is needed; do not enable `expose_tokens` for this feature.
4. Keep `RELINK_HISTORY_MODE=oidc` (the default) and leave history enabled. Restart
   Streamlit and open **http://localhost:8501**, consistently using that hostname.
   Click **Sign in for private history**. Verify the provider redirects back and
   that saving a search creates your account's history.
5. Before public hosting, register the exact HTTPS callback for your real app
   domain and use it for `redirect_uri`. Keep secrets server-side and preserve the
   corresponding-source/release requirements already recorded in LICENSING.md.

Configuration supports one native default provider. Auth0 or Google can use the
same adapter; no custom OAuth flow or third-party login component was added.
Incomplete configuration shows an honest unavailable message. A login-start error
shows a generic configuration error without rendering credentials. See the
[st.login configuration reference](https://docs.streamlit.io/develop/api-reference/user/st.login).

## Troubleshooting a missing sign-in button

Open **Sign-in setup details** in ReLink's Search history sidebar. It identifies
missing or empty setting names, a cookie secret shorter than 32 characters, a
missing authentication dependency, unreadable secrets, or values nested in a
named provider table. The panel never displays configured values or exception
text. This is a local configuration check, not validation of Auth0 credentials.

ReLink calls `st.login()` with the default provider. Put all five required
fields directly in `[auth]`, rather than splitting them into `[auth.auth0]`.
Changing `.streamlit/secrets.toml` locally does not update Streamlit Cloud:
edit that deployed app's **Settings → Secrets**, save and reboot.

The earlier no-login deployment example explicitly used
`RELINK_HISTORY_ENABLED = "0"`. To enable private history after configuring
Auth0, change it to `"1"` **above `[auth]`**, keeping
`RELINK_HISTORY_MODE = "oidc"`. ReLink shows an explicit hint when this switch
disables history. It never enables shared/local mode to bypass authentication.

If the button appears but login fails later, record where it stops and the
visible error wording, excluding credentials, authorization codes and callback
query strings. A reachable metadata endpoint does not establish that a client
secret, callback allowlist or complete browser login is valid.

## What is isolated

- Private files live in `.relink/history-users/<SHA-256 namespace>.json`. Namespace
  inputs are the exact OIDC issuer and subject, serialized unambiguously. Email
  changes do not change ownership; identical subjects from different issuers
  remain separate. The hash is routing, not encryption or a substitute for access
  checks. `RELINK_HISTORY_PATH` changes the base; private files use its sibling
  `<base-stem>-users` directory.
- Save, list, view, rerun, export, delete and clear only use the current account.
  Saved dialogs reauthorize and reload the record by ID, including fragment reruns.
  Switching/expiring identity resets active form/upload/result state. Remote
  actions bind their starting identity and discard results if it changes, including
  failed requests. No model/search service is called by opening saved history.
- Private export files are created as browser-local Blobs from session-delivered
  encoded JSON. They are never registered with Streamlit's unauthenticated global
  `/media` download route. Only constant application JavaScript executes; remote
  data is base64-encoded bytes, with escaped labels/attributes. No external script,
  endpoint or frontend framework was added. This requires JavaScript in the browser.
- Legacy `.relink/history.json` remains untouched and invisible to private users.
  It is not assigned to the first person who signs in. Explicit
  `RELINK_HISTORY_MODE=local` accesses that old shared single-operator store;
  never use this mode on public/shared hosting. `RELINK_HISTORY_ENABLED=0`
  disables disk history for every mode without deleting files.
- Files retain the previous per-account bounds (50 entries, 2 MiB/entry,
  10 MiB/file), atomic writes and private file permissions. Server operators
  can still access files; storage is not encrypted or isolated from that operator.
  Tokens, claims, login credentials, full PDF page text and PDF bytes are not saved.

## Expiration and verification limits

ReLink requires an unexpired `exp` as well as issuer/subject. Streamlit itself
persists its identity cookie for up to 30 days and does not automatically enforce
the token's expiry for application access. An expired identity must sign out and
sign in again; saved records remain on disk. Checks run on application actions
and reruns, not a background timer that erases an idle screen at expiry.

Streamlit logout clears the current session/cookie, but already running sessions
in other tabs remain authenticated until their own session changes or expires.
Close other tabs on a shared computer. ReLink does not implement global session
revocation. Downloads or data already delivered to an authorized browser cannot
be recalled. See [Streamlit logout behavior](https://docs.streamlit.io/develop/api-reference/user/st.logout).

Automated acceptance uses native Streamlit AppTest, mocked OIDC claims and real
temporary JSON stores. It covers two users, guests, expired/invalid identities,
stale handles/fragments, identity changes during successful/failed requests,
private export payloads and legacy-store separation. It does not verify Google/
Auth0 redirects, real browser cookies or physical browser download behavior.
Provider credentials and a manual browser walkthrough are still required for
those checks. No real OAuth application has been configured by this task.

The local filesystem must survive restarts for persistence; ephemeral cloud disk
does not. Use one application process per store. Per-account bounds do not cap
aggregate storage across unlimited signups; public deployment still needs normal
capacity controls alongside the existing network/PDF/source-release gates.
