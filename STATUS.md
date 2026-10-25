# ReLink status

Updated: 2026-10-25 local time and UTC.

## Current Auth0 troubleshooting — safe configuration diagnostics

- Owner reports sign-in still fails after configuration. Earlier screenshot
  showed both missing/unrecognized login configuration and explicitly disabled
  history. The exact current failure stage is requested; Cloud secrets and the
  Auth0 application's settings cannot be inspected from this workspace.
- A real read-only request to the owner's public Auth0 discovery endpoint
  returned HTTP 200, the expected issuer, and authorization/token/JWKS/logout
  endpoints. No credentials were sent. This verifies domain/discovery reachability,
  not client credentials, callback allowlists or successful sign-in.
- An isolated real Firefox guest session reached the deployed app's embedded
  frame at /~/+/. Its sidebar still reports unrecognized sign-in configuration
  and has no login button, while history is now enabled (guest sign-in prompt,
  not the previous explicit-disabled message). No credentials were entered,
  saved history accessed, or login submitted; this narrows the live blocker to
  the application's local configuration/dependency check before Auth0 redirect.
- Found an observability problem: all configuration failures produced the same
  generic unavailable message. Added a native Sign-in setup details expander
  with static field-name diagnostics for missing/empty settings, short cookie
  secrets, named-provider nesting, missing Authlib and unreadable secrets.
  Configured values and exception bodies are never displayed. The existing
  native default-provider flow and identity isolation remain unchanged.
- Disabled history now points to RELINK_HISTORY_ENABLED = "1" above [auth],
  retaining oidc mode. The old no-login demo template used "0"; no settings are
  enabled automatically and local/shared fallback remains prohibited.
- Regression tests first produced four expected failures; all five now pass.
  Focused auth/history checks: **28 tests/17 subtests pass** in 5.60s. Fresh full
  suite: **278 tests/192 subtests pass** in 15.03s. Compilation and whitespace
  checks pass. All automated credentials/identities are fixtures; no live login
  is represented by these tests. No dependencies or remote requests added to UI.
- Published diagnostic fix `78bd975` to GitHub main; push confirmed. Preserved
  the owner's newer Dev Container commit by fetching/rebasing before publishing.
  A second real guest-browser check confirms the updated panel is deployed.
- The deployed panel identifies **all five auth fields as missing/empty** under
  the expected [auth] table: redirect_uri, cookie_secret, client_id, client_secret
  and server_metadata_url. No missing-dependency issue is reported. This is the
  observed pre-redirect blocker; the operator must save those settings in this
  specific Cloud app's Secrets and reboot. The workspace's local files also
  lack auth values, but they do not establish what was entered in Cloud.
- Auth0 end-to-end login remains unverified: no login button is available until
  configuration is corrected, and no user credentials were entered. Durable
  cloud history is still separate. Verification summary is recorded in
  docs/readiness/auth-configuration.json; no secret values or callback tokens.

## Latest fix — navigation overlap reproduced in Firefox

- Owner's screenshot exposed a regression in the compact navigation. The brand
  was absolutely positioned, but its reserved tab spacing targeted removed
  BaseWeb selectors. Installed Streamlit 1.66.1 has ARIA tabs and no matching
  BaseWeb tab lists. Firefox reproduced the real overlap; the initial geometry
  assertion failed with `Brand overlaps Find datasets`.
- Removed the brand overlay entirely. A native horizontal brand row now sits
  above the native tab strip in normal document flow; ARIA selectors restore
  active/hover/focus styling. Missing custom CSS safely leaves a stacked native
  header. Three eager tabs, workspace state, search behavior and source access
  are preserved. No engine or dependency changes.
- Real local Firefox checks pass at 1688, 1024, 768, 640, 390 and 320px: no brand/tab
  overlap or page overflow. Desktop/mobile screenshots were visually inspected.
  Browser tab activation and missing-custom-CSS fallback also pass. Evidence and
  reproducible diagnostic: docs/readiness/navigation-layout/ and
  scripts/check_navigation_layout.py. No search was submitted by this check.
- Fresh complete suite: **273 tests/192 subtests pass** in 15.85s; focused UI:
  **25 tests/6 subtests pass** in 6.40s. Compilation and whitespace checks pass.
  Earlier AppTest-only verification did not establish visual correctness; the
  former browser-tool limitation was overcome using isolated local Firefox.
- Published fix `4aa747d` to GitHub main; push confirmed. Hosted Cloud acceptance
  is still separate from these actual local browser checks; refresh after the
  updated main deploys. Temporary local app/browser processes were stopped.

## Latest UI milestone — compact navigation and useful interactions

- Owner's deployed-app screenshot requested structural changes beyond color:
  ReLink in a top bar, dataset/paper/license-source tabs and useful interaction.
  Replaced the large hero and above-fold legal block with a compact native brand
  and three-tab navigation. License/warranty/source links now live in the third
  tab, after Find datasets and Find papers.
- Paper search now has a focused input card, concise workflow guide and three
  clickable topic presets. Dataset presets fill the actual Iris DOI or historical
  MNIST URL and switch the appropriate input mode. They never start service calls
  or manufacture results; explicit Find is still required. Callbacks give native
  toast feedback, clear stale dataset results and preserve account-scope checks.
- Native eager tabs retain both workspaces' widget/results state. Scoped CSS
  aligns brand/navigation, adds active/hover/focus feedback, keeps the starfield
  and small planet mark, and handles mobile/reduced motion. No giant hero, remote
  assets, engine changes or dependencies.
- Tests were observed failing before implementation. Fresh full suite:
  **273 tests/192 subtests pass**, no failures/skips; docs/readiness/navigation-pytest.log.
  Focused UI suite:40 tests/6 subtests. Compileall and whitespace checks pass.
  Independent read-only review found no critical/important issues; it separately
  passed four navigation tests. No live provider recheck was needed for UI-only
  changes; earlier live evidence remains dated and unchanged.
- Browser executor discovery still returns no execution tool; exact updated
  visual alignment/hosted acceptance remains unverified. Published UI change
  `4f71403` to GitHub main; push confirmed. Refresh/reboot and inspect after Cloud updates.

## Latest milestone — combined dataset AI and space workspace

- Owner confirms hosted paper search works and authorizes Gemini dataset ranking
  alongside existing methods, tiny header/three-row previews, and a space theme.
  Design/plan: docs/superpowers/specs/2026-10-25-dataset-ai-space-design.md and
  docs/superpowers/plans/2026-10-25-dataset-ai-space.md. No new billing/services.
- Preview milestone implemented independently: public-only streamed prefixes,
  Range hints with a real 64 KiB cap, UTF-8 CSV/TSV header and at most three complete
  rows, explicit malformed/truncated/unsupported/error outcomes. At most three
  advertised file attempts per assessed batch; other formats use metadata only.
- Combined ranking preserves deterministic points and verification labels;
  verified identity, exact identifier evidence and version/hash conflicts retain
  authoritative tiers. Gemini orders actual IDs/evidence references within tiers.
  Model failure preserves original ordering; candidates beyond the model cap
  remain visible with an explicit limitation. One assessment per combined batch.
- Native topic/name/DOI search, URL/PDF and selected-paper combined datasets are
  connected; metadata/sample disclosure precedes Find. Cached ten-at-a-time
  dataset pagination makes no requests. History/export includes typed assessment
  and preview snapshots, retaining existing identity rechecks and older defaults.
- Original CSS space theme implemented: navy starfield, amber planet/orbits and
  primary buttons, cyan focus/evidence accents, responsive/reduced-motion styles.
  No external images/fonts, movie artwork, new frontend or extra dependencies.
- Fresh final full suite: **269 tests/192 subtests pass**, no failures/skips;
  docs/readiness/dataset-space-pytest.log. Compilation, pip check and whitespace
  checks pass. No dependencies added. Real sampler read15,241 bytes/three rows
  from the official public penguin CSV and Gemini assessed its actual sample.
  Separate exact DataCite Iris DOI lookup returned the real record and AI reason;
  status remains likely_match, not verified. Evidence: dataset-ai-exact-live.json.
- Initial broad topic query returned30 actual but weak metadata leads, preserved
  in dataset-ai-live.json. DataCite now explicitly requests relevance sorting;
  coverage/keyword retrieval can still miss relevant datasets. No candidate or
  successful recovery was invented to hide that limitation.
- Independent review found two important integration issues: combining could lose
  initial URL/DOI/hash evidence, and paper actions lacked sample disclosure. Both
  were reproduced RED then fixed GREEN. Actual uploaded-PDF hash/URL retention,
  named-version warnings, processing disclosure, model-cap tails and snapshot
  round trips pass. Name-only version mismatch warns without asserting identity.
- Docs/demo/attribution updated. Published to GitHub main in engine commit
  `0eebe9a` and space-workspace commit `6d0ad3b`; push confirmed.
  Browser execution tooling remains unavailable, so actual
  visual/updated hosted acceptance is not inferred from AppTest or CSS checks.

## Latest fix — Gemini generation request budgets

- Owner reported `Gemini ranking: timeout` after the evidence-format fix. Code
  inspection found generation POSTs inherited the ordinary 10s read-inactivity
  and 30s cooperative elapsed limits. A real local before-check completed in
  3.793s with the old limits; the exact hosted delay/cause was not reproduced.
- Added validated per-POST read/elapsed overrides. Both Gemini paper ranking and
  dataset identification now use 60s read inactivity and a 90s cooperative elapsed
  budget, while DNS/connect/write/pool remain 10s. Ordinary URL, Archive, DataCite
  and paper-source requests keep their existing limits. No shared-client mutation,
  retries, model/payload changes, credential changes or billing upgrades.
- New mocked regressions first failed, then passed: simulated 20s generations,
  unchanged before/after ordinary requests, elapsed-budget clamping/expiry,
  invalid overrides and genuine timeout fallback with one request only.
  Fresh full suite: **209 tests and 181 subtests pass**, no failures/skips;
  docs/readiness/generation-timeout-pytest.log. Compilation, pip check and
  whitespace checks pass. Independent read-only review found no important issues.
- Separate real after-check accepted all 26 supplied public-paper abstracts in
  3.369s and observed read=60/connect=write=pool=10. Evidence:
  docs/readiness/paper-ranking-timeout-before.json and -after.json. This confirms
  actual request configuration and successful generation, not a real 20s delay
  or hosted-browser acceptance. The elapsed budget remains cooperative and
  cannot preempt every internal slow-header read; no strict wall-clock claim.
- Documentation updated; fix `2c0e158` pushed to GitHub main and confirmed.
  Genuine model
  delays/network failures still return explicit keyword fallback. Run a fresh
  search after the deployed app updates; saved fallback results do not rerank.

## Latest fix — intermittent Gemini paper-ranking rejection

- Owner reported `Keyword fallback · Gemini ranking: invalid response` in the
  hosted UI. Their quota screenshot shows usage below displayed free-tier limits;
  this message follows validation, while HTTP 429 has a distinct status. The exact
  hosted topic/response was not supplied. A local replay succeeded, confirming
  intermittency; earlier actual diagnostics had found overlong model quotes.
- Replaced model-written quotes with numbered passages built from actual bounded
  abstract text (16 words/240 characters each). Gemini returns a paper ID, its
  selected passage ID and a reason; ReLink supplies/checks the source text locally.
  Complete known paper IDs and valid own-paper passage IDs remain mandatory.
  No URLs or verification claims come from model output. Existing result/history
  contracts remain compatible. No retries, dependencies, extra model calls or
  billing changes. Unreadable/oversized tokens are skipped without joining gaps.
- Added safe specific rejection details: malformed/incomplete JSON, output token
  limit, wrong paper count, unknown/duplicate paper IDs, invalid passage reference
  or overlong reason. Raw model response/error bodies and keys are not displayed.
- Tests were written and observed failing before implementation. Fresh full
  suite: **203 passed, 169 subtests passed**, no failures/skips; output in
  docs/readiness/paper-ranking-grounding-pytest.log. Existing pagination, dataset
  handoff, history compatibility and identity-isolation tests continue passing.
- Real fixed flow accepted **26 first-batch papers and 25 unseen next-batch
  papers**, both source APIs responding and no previous identity repeated.
  Separate evidence: paper-ranking-grounding-live.json and -next-batch.json;
  earlier quote-generation observations are preserved. Two live checks do not
  guarantee every future model response or prove the exact hosted issue resolved.
- Independent read-only review found no critical/important issues. Persisted
  additional regressions for later passage references, cross-paper reference
  rejection, control-token gaps, the 30-paper guard and large Unicode payloads.
  Compilation, pip check, whitespace and configured-key exclusion checks pass.
  Documentation updated; fix published to GitHub main as `08601df` and push
  confirmed. Refresh/reboot the hosted app and run a fresh Find papers action;
  earlier cached fallback snapshots do not rerank automatically.
  Updated hosted-browser verification remains unavailable in this session.

## Latest milestone — 30-paper abstract ranking and Load more

- Owner authorized implementing the previously discussed paper-search upgrade.
  Added OpenAlex plus official arXiv retrieval (15 records each per batch),
  conservative DOI/arXiv deduplication retaining source records and PDF leads,
  and one abstract-only Gemini ordering request per explicit search.
- Model IDs must exactly cover the supplied papers, and short supporting quotes
  must occur in the actual supplied abstract excerpts. Invalid output, missing
  configuration, model errors/quota/timeout use explicit keyword fallback.
  Relevance reasons remain AI judgments, not verified facts or probabilities.
- Streamlit shows ten at a time; Load more reveals cached results without HTTP
  requests. Search more explicitly requests the next source pages, excludes prior
  identities, and labels ranking relative to its new batch (three batches maximum).
  Selected-paper dataset lookup and identity checks remain connected.
- Fresh final verification: **191 tests and 159 subtests pass**, no failures/skips;
  docs/readiness/paper-ranking-pytest.log. New mocked tests cover model ID/quote
  rejection, synonyms, bounded inputs, missing abstracts/key, quota/timeouts,
  partial sources, pagination and real-module Streamlit dataset handoff.
  Compileall, pip check, whitespace and configured-key exclusion checks pass.
- Read-only review found two important defects, reproduced RED then fixed GREEN:
  populated winner URLs could lose another record's arXiv alias; provenance now
  retains each source's landing/PDF URLs for dedup and subsequent batches.
  A skipped malformed record could disable Search more; paging now uses raw page
  fullness independently of usable count. Full suite passes after both fixes.
- Real first/second source pages each returned 15 OpenAlex plus 15 arXiv records.
  Latest first batch had 29 unique records/three missing abstracts; Gemini output
  was rejected and 24 keyword matches remained. Explicit second batch accepted
  **25 Gemini-ranked unseen papers**, every quote locally checked and no previous
  identity repeated. See paper-ranking-live.json and -next-batch.json under
  docs/readiness. Model output can still fail validation; no automatic retries.
  Earlier checks and sandbox DNS failures remain separate, never app data.
- No dependencies, Scholar/ResearchGate scraper, bulk PDF analysis or billing
  upgrade added. Abstract excerpts are capped at 48,000 characters overall.
  arXiv serialization applies within this process; scaling workers needs a shared
  limiter. Existing native PDF/parser and transport header-deadline limits remain.
- README, provider attribution, paper/Gemini docs and demonstration steps updated.
  Published to GitHub main in focused engine (`a907885`) and UI/evidence
  (`103b223`) commits; git push confirmed the remote update. Hosted-browser verification of this new
  version remains blocked by unavailable browser tooling; owner confirmation
  below applies to the earlier deployed build. Auth0 remains deferred.

## Latest deployment check — owner supplied the hosted address

- Subsequent owner browser checks confirm that ReLink's app page loads and
  searching for a paper appears to work. This is user-reported hosted acceptance,
  separate from the agent's HTTP probes. No exact query/result payload was
  supplied. Selected-paper dataset lookup, PDF/Gemini results, URL recovery and
  browser exports are not established by that paper-search observation alone.
  That observation predates this turn's 30-paper Gemini ranking/Load more upgrade.
  Auth0 remains deferred.

- Owner supplied https://relink.streamlit.app/ after the dashboard deployment
  handoff. At 2026-10-25T05:48:04 UTC, approved cookie-aware HTTPS requests
  reached that hostname and returned HTTP 200. The root's normal Cloud cookie
  exchange completed through share.streamlit.io and returned to the supplied URL.
- Root HTML is the Streamlit Cloud JavaScript wrapper, not rendered ReLink
  controls. /_stcore/health returned that same HTML (200, 9,782 bytes), not the
  expected plain ok. Therefore the address is reachable, but underlying Python
  runtime health and successful app startup are **unverified**, not PASS/FAIL.
- Current browser-control tool discovery still exposes no execution tool, so
  hosted URL/PDF/Gemini flows, private-source link, history-disabled setting,
  deployed commit and physical downloads have not been inspected. Asked the
  owner whether the browser shows ReLink, a startup error, or an access page.
  No application-code failure is inferred solely from the Cloud shell.
- Saved sanitized live observations/assessment in
  docs/readiness/hosted-deployment-http.json. No response cookies or auth query
  payloads are stored. The configured key was not observed in fetched HTML;
  that limited check does not audit every client response. Restricted sandbox
  ConnectError attempts are separate in hosted-deployment-http-sandbox.json.
  Initial curl without cookies looped; cookie-aware execution completed normally.
- No source/runtime changes or new mock/live dataset results were introduced.
  Existing 173-test/142-subtest preflight remains the automated evidence, not
  proof that those flows pass on the hosted environment. Auth0 remains deferred.

## Latest milestone — Streamlit deployment prepared; account action pending

- Owner authorized deploying the current tested demo to Streamlit Community
  Cloud, with history disabled and Auth0 deferred. Rechecked repository main,
  app.py, Python 3.12 requirements and official deployment/secrets documentation.
  No new paper-search feature or hosting migration was added.
- Fresh complete preflight: 173 tests and 142 subtests passed in 11.66s.
  Saved output: docs/readiness/deploy-preflight-pytest.log. Source/workspace started
  clean at 9791fcb. No new live-provider or hosted-browser success is claimed.
- Prepared owner-only .relink/streamlit-cloud-secrets.toml with the existing
  Gemini key/model, RELINK_HISTORY_ENABLED="0", oidc mode and pinned public
  corresponding-source URL. Syntax, disabled history and mode 0600 verified;
  git check-ignore confirms it cannot enter ordinary commits. Existing secrets
  file was not changed; no key printed or sent to a remote service by this step.
- Browser skill workflow discovery found no browser-control execution tool.
  No Streamlit deploy connector is available; plugin search returned no matching
  integration. There is no authenticated deployment path in this session.
  Prepared docs/DEPLOYMENT.md with exact fields; the owner must sign into the
  Streamlit dashboard and submit the private settings/deployment. This is a
  concrete tool/account-access limitation, not another approval request.
- Hosted URL, health, engine requests, physical browser downloads and actual
  cloud secret loading remain unverified until a deployment exists. No live
  application URL is invented. Known PDF/header-deadline limits remain recorded.

## Latest milestone — GitHub publication

- Published https://github.com/crqzyexprees/relink as a public repository on
  2026-10-25. Added origin and pushed main with upstream tracking. GitHub API
  confirms private=false; a separate anonymous raw README request returned
  HTTP 200. All project code, license/notices, docs and checked evidence are
  committed. No actual secrets, local history, PDFs or virtual environment.
- Five focused new commits initially published: ddd1f62 licensing, 783ede7
  dataset engine, dede46e paper/PDF/Gemini pipeline, ed00e67 UI/private history,
  fe49f05 docs/evidence/next-search proposal. A follow-up records publication.
  Original 03ffb3e remains unchanged. No rewritten or backdated history.
- Final prepublication suite: 173 tests and 142 subtests passed in 11.39s.
  Staged source snapshots independently passed as listed below. Scanned 139
  committed blobs for the configured Gemini key: no matches. Staged credential
  pattern/private-path scan also had no findings; this is not a complete audit.
- Updated source/publication statements in README, attribution and licensing
  docs. Set RELINK_SOURCE_URL to the exact deployed commit when hosting; no hosted
  deployment or actual OAuth/browser acceptance was performed. Streamlit Cloud
  remains the recommended demo host; Auth0 configuration is deferred.

- Owner requested pushing the project to one GitHub repository in meaningful
  commits. The checkout initially had one URL-recovery commit and no remote.
  GitHub CLI is signed in as crqzyexprees; a read probe found no accessible
  crqzyexprees/relink repository. Proposed that public destination; the owner's
  subsequent okay is treated as approval for this open-source repository.
- Created focused licensing, dataset-engine, paper/PDF/Gemini and UI/private-
  history commits, using actual creation timestamps. Independently checked staged
  snapshots in clean temporary source directories: engine 70 tests/85 subtests,
  paper pipeline 112/116, complete app 173/142, all passed. Saved output under
  docs/readiness/staged-*-pytest.log. Fresh working-tree preflight also passed
  173 tests/142 subtests. This is not a new dependency-clean install.
- Reviewed all publishable files (118 before new docs/logs, about 1.3 MB, text
  only). No configured Gemini key, common credential pattern, private-key header,
  real secrets file, environment or local history was found among Git inputs.
  License/notices and genuine dated readiness evidence are included. Private
  files remain ignored. This scan is evidence, not a comprehensive secret audit.
- Git writes need approved execution because .git is read-only inside the sandbox.
  Scoped Git approvals succeeded. No force push, backdated commit or rewrite of
  the original commit was requested/performed. Remote creation/push and anonymous
  publication verification subsequently succeeded as recorded above.
- Recommended Streamlit Community Cloud for the current architecture, with
  server-side Gemini/source configuration and disk history disabled while Auth0
  is deferred. Added docs/DEPLOYMENT.md. Vercel connector required reauthentication;
  used official documentation as fallback. No hosted app has been deployed/tested.
- Owner's next paper-search idea is recorded in docs/PAPER_SEARCH_NEXT.md:
  OpenAlex/arXiv retrieval up to 30 unique papers, grounded Gemini abstract
  reranking, ten displayed plus Load more, selected-paper dataset lookup. Scholar
  and ResearchGate are proposed as manual external links because of their access
  restrictions. No new search functionality or fake results were implemented.

## Latest milestone — private per-account history

- Owner requested history isolation and Streamlit documentation. Reviewed native
  st.login/st.user/st.logout docs and installed implementation. Added a small
  history_access.py adapter using trusted OIDC issuer/subject plus unexpired exp.
  Email, form fields, query parameters and arbitrary paths are never identities.
  Default mode is now oidc: guests can search but cannot read/save disk history.
  Missing/malformed/expired identity and invalid config fail closed. Explicit
  RELINK_HISTORY_MODE=local remains a shared single-operator exception; never
  use that mode for shared/public hosting.
- Per-account stores live in .relink/history-users/<opaque namespace>.json and
  retain existing entry/file limits, atomic writes and private file permissions.
  Save/list/view/rerun/export/delete/clear are scoped to the current identity.
  Existing .relink/history.json was neither migrated nor assigned to a user; it
  remains untouched and invisible to private accounts. Native provider identity
  and retained server disk allow reopening the same account across restarts.
- Active forms/uploads/results reset on identity change/expiry. Saved dialogs
  reauthorize and reload their ID inside the current namespace. True fragment
  denial forces a full app rerun, clearing previous main-page state too. All four
  normal remote actions and saved reruns bind their starting identity, recheck
  before saving/rendering, and reset state on success or failure if it changes.
- Review reproduced three privacy gaps: ordinary Find could save into a changed
  identity, standard Streamlit download media URLs do not check authentication,
  and a denied dialog fragment left old main-page state. Added failing-then-passing
  regressions and fixed all three. Also rejected malformed huge expiries/surrogate
  claims without crashing. Follow-up review found no remaining important finding
  in its scope; focused isolation tests pass 17 tests and 17 subtests.
- Private reports/history export via browser-local Blobs from session-delivered
  base64 JSON; no global unauthenticated /media download is registered. Only
  static owned JavaScript executes, with encoded payloads and escaped attributes;
  remote content never becomes code. Native downloads remain in explicit trusted
  local mode. Already delivered/browser-downloaded data cannot be recalled.
- Enabled Streamlit's official auth extra; approved pip installation added
  Authlib 1.9.1, joserfc 1.7.7, cryptography 50.0.2, cffi 2.1.1 and pycparser 3.12.
  Incremental license metadata/hashes and install output are saved in
  docs/readiness/auth-dependencies.json and auth-install.log. No provider account,
  OAuth application, billing change, deployment, staging or commit was performed.
  Real secrets were not edited; a blank secrets.example.toml and docs/AUTH.md
  explain provider client ID/secret, callback and private random cookie secret.
- Full fresh offline suite: **173 passed, 142 subtests passed**, no failures/skips,
  in 9.45s. Evidence: docs/readiness/history-isolation-pytest.log/xml. Tests use
  mocked OIDC/service boundaries and real temporary stores/native widgets; test
  apps use fake secrets instead of reading the operator's secrets. Compilation,
  pip check, whitespace and secret/history ignore checks pass. No test records
  were written into real history. Prior clean install still covers 95 tests;
  this milestone did not rerun a fresh environment installation.
- **Still unverified:** actual Google/Auth0 login redirects/cookies and physical
  browser Blob downloads. OAuth client credentials/callback have not been supplied
  or configured; the Gemini key is not a login credential. No live login success
  is claimed. Token checks run on actions/reruns, not an idle expiry timer.
  Streamlit logout does not revoke existing sessions in other tabs; global session
  revocation is outside this scope. Server operators can read local files; no
  encryption or unlimited-account storage quota was added. Existing browser,
  source-release, strict header deadline and PDF process-isolation gates remain.

## Latest milestone — Gemini incorporated into paper/PDF discovery

- Owner supplied a private key, then explicitly requested core integration rather
  than an optional feature. Analyze PDF → Find and Find papers → Find datasets
  now run Gemini identification automatically, then search real DataCite records
  for supported names. No separate toggle, new dependency or billing change.
  URL-only recovery and abstract keyword ranking remain independent of the model.
- Added gemini_config.py, gemini_models.py, providers/gemini.py, gemini.py and thin
  shared rendering in gemini_ui.py. Reused one PDF parse to retain bounded page
  text in memory. Readable link-free PDFs now support identification. Page text,
  prompts, keys and PDF bytes are excluded from saved reports/history; short
  accepted excerpts and repository snapshots persist. Uploaded-only saved entries
  need reupload to rerun. Existing saved schemas remain compatible.
- One generation per explicit action, 48,000 supplied characters, 8,000/page,
  eight mentions, 240-character/24-word quotes, three name searches and five
  repository candidates/name. No automatic calls on upload, tab selection, ordinary
  reruns or saved-result viewing. Missing key, auth errors, malformed/empty output,
  429/Retry-After, timeout and provider errors stay distinct; independent results
  survive. Per-name invalid queries no longer abort other results.
- Names/versions/pages and quotes are checked against supplied source text. Model
  paraphrases are rejected; if the name occurs on the claimed page, a real local
  excerpt may replace the rejected quote with an explicit label/warning and partial
  status. A mention does not prove study use or dataset identity. Only real
  repository responses create resource candidates; no generated URLs/hashes.
- Keys load server-side from environment or ignored .streamlit/secrets.toml, stay
  out of repr/history/reports and use a per-request HTTPS header to a fixed Google
  host. POST bodies/responses are bounded and redirects never forward credentials
  or bodies. Existing public DNS/IP pinning, Host/SNI and request limits apply.
  UI discloses Google excerpt processing before Find; public/nonconfidential
  papers only. No real key was printed. Git ignore and an actual-key scan of
  code/docs/history passed with no matches.
- Initial live model 2.5 access returned HTTP 404; current Google model docs
  explain restrictions for new projects. Switched to gemini-3.5-flash-lite,
  documented as free-tier eligible and confirmed accessible with this key.
  Google project billing/quotas were not inspected or changed; free-tier model
  eligibility is not independent verification of an account's billing settings.
- Separate real check at **2026-10-25T04:45:20 UTC** parsed the actual public SQuAD
  PDF: seven supported mentions (SQuAD, ImageNet, Penn Treebank, MCTest, WikiQA,
  Children's Book Test and BAbI). Five AI quotes needed real local excerpts,
  explicitly flagged; result is **partial**. DataCite returned five real records
  for each of the first three names. These are candidates, not fifteen recovered
  datasets; study use, file identity/availability and versions remain unverified.
  Evidence: docs/readiness/live-gemini.json. Earlier failed model/grounding runs
  remain separate. No saved live artifact is used as production fallback data.
- Full offline suite: **156 passed, 125 subtests passed**, no failures/skips, in
  7.00s. Evidence: docs/readiness/gemini-pytest.log/xml. Includes real native
  Streamlit actions over mocked external HTTP/DNS, link-free uploads, history,
  quotation/hallucination rejection, bounds, auth/429/timeout/redirect/error cases
  and key isolation. Tests never load the owner's key or contact live services.
  Read-only code review's invalid-name finding was fixed with a failing-then-passing
  regression; follow-up review found no remaining high-risk finding in its scope.
- Setup, attribution, plans, history, readiness and demo docs updated; details in
  docs/GEMINI.md. No dependency changes, clean-install rerun, commits, publication
  or submission. Earlier clean install remains 95 tests. Browser visual acceptance,
  corresponding public source/release checks, strict HTTP header deadlines and
  native PDF process isolation remain open.

## Latest review — HackPSU and MLH track fit

- Checked the official event-specific Fall 2026 Devpost categories, requirements,
  and rules, plus relevant provider documentation. Saved prioritized proposals in
  docs/HACKPSU_TRACKS.md. Research is the strongest current project fit; optional
  grounded AI identification of named datasets is the most relevant sponsor-oriented
  addition. Private authenticated history and a reproducible deployment are useful
  alternatives, requiring their own configuration/scope decisions.
- Surfaced the conflicting submission deadline displays and advised creating the
  submission before the earlier published requirement and checking with organizers.
  Eligibility/category combinations must be confirmed rather than assumed.
- No feature/provider integration, credentials, sponsor signup, billing, deployment,
  message, or submission was performed. No tests rerun for this documentation-only
  review; prior complete result remains 142 tests plus 119 subtests passing.

## Latest milestone — persistent local history

- Owner requested history survive browser closure/app restart. Added a bounded,
  versioned JSON store in relink/history.py and a separate history_ui.py sidebar/
  snapshot viewer. Default location is project-root/.relink/history.json, ignored
  by Git. No database, account system, new dependency, or external service.
- Completed URL/PDF-link recovery, paper searches, and paper-dataset lookups are
  saved on explicit actions, including empty/failed provider outcomes. Ordinary
  reruns do not save duplicate entries. No uploaded/downloaded PDF files or bytes
  are persisted; report context/abstracts/metadata and filenames/hashes may be saved.
- Sidebar offers View saved results (no network), Search again (explicit requests,
  new dated entry), delete, clear, and JSON export. Saved results show original
  snapshot dates and are not presented as fresh checks. Current form state remains
  separate. Arbitrary history-file import and per-user/browser storage are deferred.
- Store limits: 50 newest entries, 2 MiB per entry, 10 MiB total with oldest-entry
  pruning. Restricted new-file permissions, process-wide thread lock, fsync, and
  atomic replacement protect writes. Declared-model JSON decoding uses no pickle
  or user-supplied type names. Corrupt/incompatible files are not silently replaced.
- Disk/size failures preserve current results and the old history. Independent
  review found an oversized Search again fallback bug; regression first failed,
  then passed after separating live-result rendering from persistence validation.
  Rerun results that cannot be saved remain visible and explicitly marked unsaved.
- Shared local workspace scope is explicit in UI/docs. Server default now binds
  to 127.0.0.1. RELINK_HISTORY_ENABLED=0 disables disk history; trusted
  RELINK_HISTORY_PATH can override the path. Public/shared hosting without per-user
  storage should disable this feature. Use one app process per history file.
- Fresh complete pytest: **142 passed, 119 subtests passed**, no failures/skips.
  Evidence: docs/readiness/history-pytest.log/xml. Tests include a separate Python
  process reopening saved data and a fresh Streamlit AppTest session viewing without
  service calls, thread concurrency, retention/delete/clear, schema/size limits,
  corrupt files, failed writes, disabled history, reruns, and unsaved oversized
  results. Automated history tests use temporary paths, never real workspace data.
- Compilation, pip check, whitespace checks, ignore rule, and localhost config
  verified. No new live provider requests were needed for disk persistence. Browser
  visual review remains pending. README/.env.example/PLAN and docs/HISTORY.md updated.

## Latest milestone — code, UI, and reliability review

- Reviewed current engine/network/providers, ranking/deduplication, PDF handling,
  state and both tabs. Independent read-only review reproduced and rechecked the
  provider/network issues. Findings, fixes, evidence and open limits: docs/REVIEW.md.
- Fixed IP-pinned pooled TLS connections crossing hostname boundaries: default
  connections no longer reuse keep-alive. Offline regression uses real HTTPX/
  httpcore with a fake backend and observes each hostname's own handshake.
- Added a cooperative 30-second fetch budget across redirect/body checkpoints,
  reducing subsequent I/O and default DNS timeout budgets. Slow headers inside
  HTTPX can still exceed it: strict lower-level wall-clock cancellation remains
  open. Preserved deterministic evidence in docs/readiness/header-budget.log and
  header-budget-repro.py. This is not a hard deadline or full workflow timeout.
- Fixed safe percent-encoded path identity (CIFAR %7E versus ~), preserving query
  bytes, encoded dots/reserved separators, meaningful slashes, and raw provenance.
- Changed ranking to whole-word metadata/author matches and half-weight partial
  title matches; reduced repeated tokenization. Iris/Irish no longer receives the
  same identity support. Existing partial-title behavior still passes tests.
- Filtered selected-paper DOI aliases from dataset link choices; all providers
  now classify deeply nested JSON RecursionError as invalid_response.
- Action errors persist across unrelated reruns without repeating requests and
  clear on relevant input changes. Paper search copy is shorter; matching details
  are expandable and long abstracts show a preview/full-text option. Removed
  environment-variable setup instructions from the product's source-link warning;
  deployment instructions remain in README. Existing backgrounds/theme retained.
- Fresh full pytest run: **128 passed, 116 subtests passed**, no failures/skips.
  Saved review-pytest.log/xml under docs/readiness. Regression cases were observed
  failing before fixes. Compilation, pip check, and whitespace checks passed.
- Four real host checks at 2026-10-25T03:29:28 UTC all returned operational results:
  example.org working, CIFAR archive capture found (20260607155414), DataCite
  Iris/Fisher search with true Iris results ahead of the unrelated/unverified marine
  record, and forest/carbon paper search found. Actual responses/times are saved
  in docs/readiness/review-live.json. No mocks/fallbacks used as live evidence.
- No dependency upgrades, additional providers, commits, or publication. Prior
  clean-environment evidence remains 95 tests, not a rerun of the new suite.
  Browser desktop/mobile acceptance, strict HTTP header cancellation, native PDF
  process isolation, and public source/release checks remain explicitly open.

## Latest design update — background and workspace panels

- Follow-up from screenshot feedback: broadened the background fade with multiple
  opacity stops, softened the grid and panel tint, removed the bright left edge,
  and made the Streamlit header transparent to avoid the abrupt horizontal color
  seam. Fixed the background relative to the viewport and increased top padding
  so the introduction panel clears the toolbar. Fresh verification: 25 UI tests
  plus 6 subtests passed; git diff --check passed. Browser visual review remains
  pending; changes were checked against the supplied screenshot and source.
- Added subtle teal/blue radial background glows and a faint 64px grid using
  application-owned CSS. No external images, fonts, animation, or dependencies.
- Added a bordered introduction panel with teal accent and copy covering papers
  and datasets. Increased desktop content width from 1080px to 1280px, reduced
  top padding, and styled the input/evidence panels with dark surfaces and soft
  shadows. Mobile padding remains bounded with a narrow-screen media query.
- License/source access, native controls, result evidence, and both tabs remain
  functional; no provider, ranking, or recovery logic changed.
- Verification: 25 UI tests plus 6 subtests passed across tests/test_app.py and
  tests/test_paper_app.py. Compilation and git diff --check passed. Browser tools
  are unavailable in this session, so visual acceptance of these CSS changes
  remains pending. The prior full-suite result is 115 tests plus 108 subtests.

## Latest milestone — topic → papers → dataset lookup

- Implemented the owner's two-tab layout: Find datasets retains URL/PDF recovery;
  Find papers accepts a topic/description, compares abstracts, and lets users
  investigate datasets from a selected paper without leaving that tab.
- Added paper_models.py contracts, providers/openalex.py bounded HTTP/parser,
  papers.py keyword ranking and dataset workflow, and thin paper_ui.py. Existing
  recovery/ranking providers are reused for selected research links. No dependencies,
  database, paid LLM, API key, or new service/server were added.
- OpenAlex retrieves up to 25 works from an application-built title/abstract query;
  local ranking only scores actual abstract keyword matches. Up to 12 meaningful
  input words and ten matched papers, ten points per match, ties explicit. Missing
  abstracts, title-only matches, malformed inverted indexes, and duplicates are
  handled conservatively. Duplicate identity keeps the strongest matching abstract,
  rather than the first record. This is keyword matching, not semantic similarity
  or a paper-quality/probability score. Details: docs/PAPERS.md.
- Selected-paper dataset lookup searches DataCite for related paper DOI records,
  extracts abstract URLs, and downloads at most one advertised public PDF on
  explicit action. The public-only pinned transport/redirect checks and existing
  PDF byte/page/text/link limits apply. PDFs stay in memory. Research links may
  be code or citations and remain explicitly unverified. No paywall bypass/crawl.
- Both tabs keep separate state. Topic/paper/link changes clear stale downstream
  results; unrelated reruns do not repeat requests. Reports/source buttons are
  namespaced so simultaneous dataset and paper reports do not collide.
- Tests were added before implementation. Complete fresh run:
  **115 passed, 108 subtests passed**, no failures/skips. Evidence:
  docs/readiness/paper-feature-pytest.log and paper-feature-pytest.xml. New tests
  cover parsing/limits/errors/429/timeouts, abstract-vs-title ranking, DOI dedup,
  selected-paper PDF/metadata partial failures, unsafe redirects, safe remote
  rendering, state changes, and native two-tab flow through real modules with
  mocked HTTP/DNS. Compilation, pip check, and git diff --check passed.
- Real approved host check at 2026-10-25T03:10:13 UTC searched
  'question answering reading comprehension dataset Stanford': 25 usable records,
  four without abstracts, ten matched papers. First was Stochastic Answer Networks
  for Machine Reading Comprehension, DOI 10.18653/v1/p18-1157, six matched terms.
  Its public ACL PDF parsed 11 pages and six research links. Related DataCite
  lookup returned a genuine empty result. Recovery of the selected GitHub code
  lead reached both providers; Archive returned 429, DataCite was empty, no candidate
  invented. Evidence: docs/readiness/live-paper-discovery.json. No automatic retry.
- Existing app health returned HTTP 200/ok. Browser visual acceptance of new tabs
  remains unverified. No new clean-environment run was done; the earlier clean
  run remains 95 tests. The known native PDF-parser hang limitation and source
  publication/dependency release gates remain open. Saved live reports are never
  used as app data. README, attribution, demo, design/plan updated.

## Latest UI milestone — link-only Find and explained options

- URL mode now needs only the URL and Find button; removed its description
  expander. PDF context remains automatically extracted and optionally editable.
  URL searches use no hidden stale PDF context. No provider/ranking logic moved
  into the UI and no unrelated candidates or additional sources were introduced.
- All returned ranked options remain visible in engine order. Each now shows its
  positive evidence without opening an expander. The first option is labeled
  best-ranked; captions explain score ties and the single-candidate case, including
  the Archive availability API's one-closest-capture limit. No claim is made that
  a single returned lead is the best surviving dataset globally.
- Renamed the action to Find and explained the optional JSON evidence report:
  structured inputs, source checks, candidates, evidence, and timestamp for sharing
  or auditing; it is not a dataset download and is not needed to read results.
- Fresh complete pytest run: **99 passed, 91 subtests passed**, no failures/skips.
  Added failing-then-passing tests for URL-only input and multiple options, feeding
  weaker-first input through the real ranking function and checking strongest-first
  rendering with visible reasons. Existing URL/PDF/export/safety tests still pass.
- Browser visual inspection remains pending. No new live provider check was
  necessary for these UI changes; the preceding real-example evidence is unchanged.

## Latest milestone — open-source preparation and real examples

- Owner authorized open-source changes after the licensing review. Selected
  AGPL-3.0-only for original ReLink code; added full LICENSE, NOTICE, README
  declaration, .env.example, and project rules preserving that choice.
- Streamlit shows the license/copyright/warranty notice and reads the source
  link from RELINK_SOURCE_URL. Missing or unsafe values produce an explicit
  warning; no repository URL was invented and no repository was published.
- Full LICENSE was copied byte-for-byte from PyMuPDF 1.28.2 upstream COPYING;
  SHA-256 57c8ff33c9c0cfc3ef00e650a1cc910d7ee479a8bc509f6c9209a7c2a11399d6.
  Dependencies retain their own licenses. No commercial purchase/parser change.
- Two new UI tests were observed failing before implementation, then passing.
  Complete fresh suite: **97 passed, 91 subtests passed**, no failures/skips.
  This run uses the working environment; the prior clean-environment run remains
  95 tests plus 88 subtests, not a rerun of the new tests in that environment.
- Seven real URL/DOI cases and one metadata search ran through existing modules
  outside the network sandbox. Inputs, source citations, exact observations,
  and limitations are in docs/evaluation.md and docs/readiness/real-examples.json.
- MNIST's historical training-images URL returned real HTTP 404 and one reported
  Archive capture. SQuAD had ConnectError plus a capture. Two old UCI pages
  redirected successfully and had captures. Iris and Wisconsin diagnostic DOIs
  returned real DataCite records. All six candidates are likely_match; no dataset
  bytes or replay access were verified. No saved report feeds the live app.
- CIFAR was working through a redirect, but its Archive target used %7E for ~;
  strict identity validation rejected it. Saved the real follow-up API response
  in docs/readiness/cifar-availability.json. No validation bypass was added.
- Iris/Fisher keyword search included an unrelated marine-monitoring result
  labeled likely_match by lexical ranking. Documented the false positive and
  recommend DOI examples for the main demo. Ranking was not changed in this task.
- Open-source preparation is implemented; public-release clearance still needs
  the real corresponding-source publication/link, contributor-rights confirmation,
  and applicable dependency/bundled-artifact checks. A public repository URL was
  requested but has not been supplied. Browser visual acceptance remains pending.

## Latest UI change — dark mode

- Set Streamlit's default theme to dark with charcoal backgrounds, light text,
  and a teal accent in .streamlit/config.toml. Native widgets and status alerts
  use the dark base theme. Removed the hardcoded light heading/card colors from
  relink/ui.py; cards now follow Streamlit's theme background variable.
- Verification: Streamlit's configuration loader reports the expected dark
  palette. `pytest tests/test_app.py -q`: 16 passed, 3 subtests passed, covering
  existing URL/PDF and result/error flows. No recovery behavior changed.
- Browser appearance remains unverified because browser automation is unavailable
  in this session. Refresh the app to load the theme; an existing saved theme
  preference may need switching to the custom theme in Streamlit Settings.

## Current readiness

Functional live acceptance passes for the preflighted dataset demo. **273 tests pass
with no skips**, plus 192 passing subtests in the working environment. Latest
paper-ranking live evidence and intermittent model fallback are recorded above. Private
history isolation passes mocked acceptance; actual OAuth/browser downloads still
need configured-provider/manual acceptance. Gemini
paper identification also passed a real check with partial grounding status as
described above. New paper
search/PDF extraction also passed live; follow-up Archive recovery was rate-limited. The prior
newly installed isolated environment passed 95 tests plus 88 subtests.
Actual Internet Archive, DataCite, a real research PDF, valid/404 URL probes, and
localhost app health all passed the live diagnostic. Visual browser acceptance
and the remaining public-release source/attribution checks remain open.

Detailed results: docs/READINESS.md. Demo: docs/DEMO.md. Dependencies and licensing:
THIRD_PARTY_NOTICES.md. Prior restricted/failed attempts remain recorded separately.

## Latest live evidence

- Approved `.venv/bin/python -m scripts.check_readiness --output
  docs/readiness/host-live-checks.json` completed with exit 0; all six checks PASS.
- Check timestamp: 2026-10-24T22:42:13.134142+00:00. No recovery/HTTP/DNS mocks.
- https://example.org/ was working; https://httpbin.org/status/404 returned 404.
- Archive availability API returned HTTP 200 and a genuine reported capture for
  https://stanford-qa.com/, timestamp 20250407122419.
- DataCite returned HTTP 200 with actual Iris DOI 10.24432/c56c76 and repository
  URL https://archive.ics.uci.edu/dataset/53. Its API schema/parse path was exercised.
- Actual SQuAD paper downloaded from https://arxiv.org/pdf/1606.05250, 10 pages,
  three extracted web links. The selected dataset URL https://stanford-qa.com
  yielded a real Archive candidate, ranked likely_match with archive_metadata_only.
  The original dataset host could not be reached; that did not suppress discovery.
- The downloaded paper is /tmp/relink-public-paper-xru82ds5.pdf; its SHA-256 and
  complete extraction/recovery report are in host-live-checks.json. It is not a
  generated fixture. No dataset bytes were downloaded or verified.
- The existing host Streamlit server answered localhost:8501/_stcore/health with
  HTTP 200 and body ok. This is a health check, not a new server-start or visual test.

## Integration fix discovered by the real paper

- The first approved live run downloaded/parsed the paper but rejected Archive's
  capture: the paper URL omitted the root slash while the API target included it.
- Preserved initial evidence in docs/readiness/host-live-before-root-fix.json.
  Its diagnostic verdict said BLOCKED, but provider invalid_response exposed an
  actual integration failure, not a permissions problem.
- normalize_url now treats an empty root path and '/' as equivalent. Archive
  comparisons use that conservative identity normalization. Raw provenance and
  original URL remain unchanged. Non-root slashes, escaped path separators, and
  query strings remain distinct, with regression coverage.
- Two new tests failed before the fix, then passed. A third guards non-root target
  mismatches. The diagnostic now reports invalid-response paper failures as FAIL
  rather than BLOCKED. The subsequent genuine live paper run passed.

## Other review fixes

- DOI resolver URLs entered into the UI populate SearchQuery.doi; DataCite omits
  the redundant constraint requiring a repository URL to equal the DOI resolver.
  Failing-then-passing regressions and a native UI/redirect integration test cover it.
- PyMuPDF minimum corrected to 1.24.3, which introduced the pymupdf module name.
- DataCite requests rightsList and preserves it in source metadata for attribution
  review. The request/provenance regression was observed failing before the fix.
- No sample candidates, fake progress, or fallback success data were introduced.
  Native UI failure tests verify provider DNS errors leave the candidate list empty.

## Automated and clean-environment verification

- Working environment: docs/readiness/pytest.log and pytest.xml, 95 passed,
  88 subtests passed; no failures/skips. JUnit includes 183 cases with subtests.
- New isolated Python 3.12 environment: /tmp/relink-clean-readiness. It initially
  had no application/test packages. Approved pip install -r requirements.txt then
  downloaded and installed dependencies normally; no packages were copied from
  the working environment.
- Clean environment: docs/readiness/clean-pytest.log and clean-pytest.xml,
  95 passed plus 88 subtests; pip check passed. Versions are recorded in
  docs/readiness/clean-environment-final.log; install output in clean-install.log.
- Working environment versions: Python 3.12.15, Streamlit 1.66.1, HTTPX 0.28.1,
  PyMuPDF 1.28.2, pytest 9.1.1. The clean environment also exercises newer allowed
  transitive versions, including anyio/certifi/idna, rather than assuming a lockfile.
- Tests cover malformed/encrypted/no-text PDFs; text/annotation/context extraction;
  real native upload/select/download widgets; original status/redirects; rate
  limits/timeouts/empty/partial results; deduplication/ranking/statuses; independent
  hash evidence; unsafe addresses/redirects/content; export; request-free reruns.
- Automated HTTP and DNS responses are mocked and explicitly separate from live
  evidence. Generated PDFs remain labeled fixtures in tests.
- Compilation and git diff whitespace checks pass. Source review found no fixture
  imports or sample-candidate fallback in production. No staging or commits made.

## Permissions and remaining acceptance

- Default sandbox execution still restricts network/socket operations. The current
  session now allows scoped approval requests; approved commands successfully ran
  live probes and clean installation outside the sandbox. Broad Full access was
  not needed for those checks.
- In-app browser automation is not exposed. Browser appearance, actual browser
  JSON download, and the latest code executing through a browser remain unverified.
  Streamlit AppTest and HTTP health do not substitute for those observations.
- Earlier DNS/socket denials are preserved in live-checks.json, its log,
  server-start.log, and earlier docs live/runtime records as historical evidence.

## Licensing and public-upload limits

- Reviewed current Artifex guidance, the upstream 1.28.2 AGPL text, installed
  package metadata/COPYING, and ReLink's direct PDF integration. Recorded AGPL,
  commercial, and parser-replacement routes with checklists in docs/LICENSING.md.
  The installed COPYING is a short dual-license summary; THIRD_PARTY_NOTICES.md
  links the full version-specific text. The subsequent owner instruction selected
  the open-source route; see the latest milestone above for implemented changes.
- 42 active Python runtime/test dependencies inventoried in
  docs/readiness/dependencies.json; exact working-environment versions, declared
  license data, source links, and discovered license-file hashes are recorded.
- Streamlit: Apache-2.0; HTTPX: BSD-3-Clause; pytest: MIT; PyMuPDF: AGPLv3 or
  Artifex commercial terms. This is not a comprehensive SBOM/vulnerability audit.
- Public release remains BLOCKED pending corresponding-source availability and
  applicable contributor/dependency checks. Project LICENSE/NOTICE now exist;
  the AGPL route was selected under the owner's open-source instruction. The
  configured public source destination has not been supplied or verified.
- Upstream lists native text-extraction hangs affecting 1.28.x; byte/page limits
  do not preempt a native get_text hang. Preflight demo papers; public arbitrary
  upload readiness needs parser upgrade/process-isolation review separately.
- Ordinary metadata never verifies dataset bytes. Independently supplied trusted
  hash evidence can be assessed, but ReLink does not download datasets or compute/
  authenticate those hashes. Scores are relevance points, not probabilities.
- Keyword matching, conservative non-root URL identity, bounded provider searches, and
  first-vetted-IP connection behavior remain documented limitations. OCR and the
  five-case real broken-dataset benchmark (M6) remain unimplemented.

## Next steps

1. Configure the native OIDC provider using docs/AUTH.md and privately supplied
   client credentials. Test two real accounts, restart persistence, logout and
   browser Blob exports. Never use shared local mode for shared/public hosting.
2. Visually inspect the running app, recover the preflighted actual paper, and
   test the JSON download in a real browser. Restart Streamlit if imported modules
   remain cached after edits.
3. Complete the selected AGPL route in docs/LICENSING.md before public deployment:
   publish corresponding release source, set RELINK_SOURCE_URL, and verify access
   and contributor/dependency obligations for the release artifact.
4. Repeat the explicit live diagnostic before presentation; a reported capture is
   an evidence-backed lead, not a guarantee that its downloadable dataset survives.
5. Review strict transport cancellation and native PDF process isolation before
   arbitrary public uploads/use. Expand to five genuinely broken dataset cases;
   current examples include working controls and do not complete that benchmark.
