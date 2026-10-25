# Private persistent history

Owner request: implement history isolation, using Streamlit documentation. This
extends the earlier local-only store without adding a database or a separate API.

## Approaches and chosen default

- Native Streamlit OIDC: durable account identity across tabs/browser restarts,
  with provider configuration required. Recommended implementation default; the
  owner can steer to session-only storage via the pending clarification.
- Session-only history: no identity-provider setup, but loses persistence on
  session closure and does not meet the prior durable-history goal.
- Anonymous browser identifiers: require another trusted cookie mechanism and
  behave as bearer credentials; not selected for this scope.

## Behavior and boundary

Use Streamlit st.login/st.user/st.logout and the supported auth dependency. No
password management, custom tokens, account signup, deployment or paid services.
Search remains available to guests; private history requires a valid signed-in
OIDC identity, including issuer, subject and unexpired token expiry. Never use
email, a typed account name, query parameters or a caller-supplied path as identity.

Derive a stable opaque namespace from the issuer/subject pair; keep a separate
bounded HistoryStore file per namespace. Authorization is enforced on every
history operation, including dialog fragments and reruns, rather than relying
on hidden widgets. Never return or rewrite another namespace. Recheck identity
after remote reruns before saving/rendering results. Clear in-session form and
result state when identity changes or expires. No global result caches.

Default to private OIDC history, failing closed for anonymous/missing/malformed/
expired identity. Missing auth configuration must not show a working login button.
Keep explicit RELINK_HISTORY_MODE=local for a single trusted desktop operator;
this is shared local storage and must not be used on shared/public hosting.
RELINK_HISTORY_ENABLED=0 still disables all disk history. Invalid modes fail closed.

Leave existing .relink/history.json untouched and invisible to private accounts;
never automatically assign shared records to whoever logs in first. No bulk import
or migration UI in this scope. Existing snapshot models/limits remain unchanged.
No keys, auth claims/tokens, full paper text or PDF bytes enter history/exports.
Hashed namespaces are routing, not encryption or protection from server operators.

## Setup and acceptance

Provide a secrets example and precise callback instructions for the native OIDC
provider, without overwriting existing Gemini secrets or fabricating credentials.
Use the same configured provider after restart for stable issuer/subject mapping.
Enforce expiration locally because Streamlit's persistent cookie does not enforce
the identity-token expiry for the application. Existing sessions in other tabs
are not revoked by Streamlit logout; document that limitation.

Offline acceptance: account A/B have separate saves, lists, views, reruns, exports,
deletes and clears; same identity reopens after a fresh session; same subject from
different issuers remains separate; guests/expired/invalid identities never open
the old shared file. Test stale dialog/rerun handles and identity switches. Run
the full mocked suite and dependency checks. Actual provider login/browser cookie
acceptance remains unverified until OAuth configuration and browser access exist.

Sources: https://docs.streamlit.io/develop/concepts/connections/authentication,
https://docs.streamlit.io/develop/api-reference/user/st.user,
https://docs.streamlit.io/develop/api-reference/user/st.login,
https://docs.streamlit.io/develop/api-reference/user/st.logout (reviewed 2026-10-25).
