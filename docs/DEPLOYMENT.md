# Hosting the current ReLink demo

Recommendation: Streamlit Community Cloud fits the existing Python app, app.py
entry point and requirements.txt. Vercel would need a separately tested hosting
adaptation. Its current WebSocket support does not itself establish compatibility
with this app's sessions/local history. This is a project-fit recommendation,
not an assertion that Vercel cannot serve WebSockets.

Sources reviewed 2026-10-25: [Streamlit deployment](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy),
[cloud secrets](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management),
[Vercel WebSockets and persistent state](https://vercel.com/docs/functions/websockets).

## Current deployment handoff

Owner supplied hosted address: **https://relink.streamlit.app/**.
The owner subsequently confirmed in their browser that the app page loads and
paper search appears to work. This is user-reported acceptance; no exact query or
response was supplied. Selected-paper dataset, PDF/Gemini, URL and download flows
still need their own hosted acceptance.
Cookie-aware public HTTPS probes on 2026-10-25 returned HTTP 200, but served the
Cloud JavaScript wrapper; even the Python health path returned wrapper HTML.
This establishes address reachability, not successful Python startup or ReLink
workflow acceptance. Actual browser/hosted URL/PDF/Gemini/export checks remain
pending. Evidence: [hosted-deployment-http.json](readiness/hosted-deployment-http.json).

The owner authorized deployment. Repository/branch/entry point are ready:

| Cloud field | Value |
| --- | --- |
| Repository | crqzyexprees/relink |
| Branch | main |
| Main file | app.py |
| Python | 3.12 |
| History | Disabled until login is configured |

The local ignored `.relink/streamlit-cloud-secrets.toml` contains the actual
server-side deployment settings, including the saved Gemini key and a pinned
source commit. It uses owner-only permissions; never upload it to GitHub or paste
its contents into chat. The file is prepared locally, not transmitted by this
task. Existing `.streamlit/secrets.toml` is unchanged.

In https://share.streamlit.io, sign in with GitHub, create an app with the fields
above, and paste that private file into Advanced settings → Secrets. Save and
click Deploy. Send only the resulting public app URL for hosted checks.

This agent session exposes neither a browser-control execution tool nor a
Streamlit deployment connector. The plugin catalog search found no matching
Streamlit deployment integration. The signed-in dashboard action therefore
required the owner, who subsequently supplied the address above. No full hosted
workflow verification has been completed in this session.

## Demo setup

1. Publish the reviewed corresponding source on GitHub. In Community Cloud,
   create an app from that repository, branch main, entry point app.py. Select
   Python 3.12, the tested runtime, in advanced settings.
2. Configure secrets in Community Cloud's app settings, never Git. For a demo
   without Auth0, use top-level TOML values like these, replacing placeholders:

   ```toml
   GEMINI_API_KEY = "YOUR_PRIVATE_KEY"
   GEMINI_MODEL = "gemini-3.5-flash-lite"
   RELINK_HISTORY_ENABLED = "0"
   RELINK_SOURCE_URL = "https://github.com/YOUR_ACCOUNT/YOUR_REPO/tree/DEPLOYED_COMMIT_SHA"
   ```

   Root-level secrets become environment variables through Streamlit. Do not add
   an incomplete [auth] section. Later, configure a real provider per AUTH.md with
   the deployed HTTPS callback, not localhost. Keep Gemini/source/history settings
   above [auth] so they remain top-level values.
3. Let the platform manage external routing/binding. The repository's local
   configuration binds 127.0.0.1 intentionally; verify that the cloud launch
   overrides it appropriately and the hosted health/page are actually reachable.
4. Run the known URL and public-paper examples on the actual deployment. Verify
   Gemini quota/access, genuine error outcomes, source links, and browser exports.
   Never describe an untested hosted build as a successful deployment.

The repository contains no saved real key or local search-history file. New
private history defaults to OIDC and never falls back to the old shared file;
explicitly disable disk history for a no-login cloud demo. Do not assume local
cloud files are durable across rebuilds or redeploys. Durable multi-instance
storage is outside this MVP.

## Current release scope

The subsequent paper upgrade adds OpenAlex/arXiv abstract retrieval, Gemini
ordering and cached Load more. Main-branch deployment can pick it up after push;
confirm the new controls in the hosted browser. Keep RELINK_SOURCE_URL pointing
to corresponding source for the new deployed revision rather than an older pin.
Latest live/model limits and test output: [PAPERS.md](PAPERS.md), [READINESS.md](READINESS.md).

Code publication and a hosted application are separate actions. No deployment has
been performed as part of preparing the GitHub commits. Real OIDC browser login,
browser Blob downloads and hosted provider requests remain acceptance steps.
Native PDF-parser process isolation and strict cancellation during slow HTTP
headers remain documented limits; use preflighted public demo papers and review
these before broad arbitrary public uploads. Complete the remaining contributor/
dependency obligations for the actual release artifact in LICENSING.md.
