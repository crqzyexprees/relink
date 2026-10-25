# Private persistent search history

ReLink saves completed dataset searches, paper searches, and selected-paper
dataset lookups to **`.relink/history-users/<opaque account namespace>.json`**
for the signed-in OIDC account. Configure login using [AUTH.md](AUTH.md). This is
actual disk storage; it survives closing the browser and restarting the app as
long as the same file is retained. It starts recording new actions after this
feature is installed; searches already lost from previous sessions cannot be
reconstructed.

Use the **Search history** sidebar:

- **View saved results:** opens a dated historical snapshot, including empty
  results and provider failures. It makes no service requests and does not change
  the active searches in either tab.
- **Search again:** explicitly makes new requests using the recorded inputs and
  saves a new dated entry. A saved PDF recovery reruns its selected URL/context;
  it does not reupload or reanalyze the original PDF.
- **Delete selected search / Clear saved history:** remove stored entries.
  Current in-session search results are separate.
- **Export history (.json):** downloads the retained snapshots for backup. It is
  an evidence record, not a dataset download. Arbitrary history-file import is
  not implemented in this version.

## Scope and privacy

The default is **private account history**, keyed by the trusted OIDC issuer and
subject. Save/list/view/rerun/export/delete/clear are restricted to that namespace.
Guests, invalid/expired claims and missing auth configuration never fall back to
the old shared file. Identity changes clear active session forms/results; actions
check identity both before and after remote work, including failed requests.
Saved dialogs reauthorize even on fragment-only reruns. Private JSON exports use
browser-local Blobs rather than Streamlit's public media URLs. No raw source HTML
is executed; export payloads are encoded inert bytes beside constant app code.

Legacy `.relink/history.json` remains untouched and invisible to private accounts.
`RELINK_HISTORY_MODE=local` explicitly enables that shared file for a trusted
single operator; do not use local mode on public/shared hosting. To disable all
disk history:

```bash
RELINK_HISTORY_ENABLED=0 .venv/bin/python -m streamlit run app.py
```

No uploaded/downloaded PDF files or PDF bytes are saved. Query text, abstracts,
extracted link context, filenames/hashes when present in reports, candidate
metadata, source URLs, scores, statuses, and timestamps **are** retained. Stored
snapshots are not independently authenticated or reverified by opening them.
The folder is git-ignored; new files use owner-only permissions. This is not
encrypted storage. Export only material you intend to share.

Dataset AI snapshots additionally retain bounded public CSV/TSV headers and up to
three sample rows per eligible file, byte/source/error details, model status and
relevance evidence. No full dataset files or request prompts are saved. Topic/DOI
dataset searches also persist as typed recovery reports without an invented
original URL. New fields have defaults so older snapshots remain readable.

## Configuration and bounds

Core Gemini identification snapshots include accepted names, short supporting
quotes, model/status and real DataCite results. No API key, full page text, prompt
or PDF bytes are saved. Reopening them performs no requests. Uploaded-PDF-only
entries require reupload to rerun; that action is disabled in saved history with
an explanation. Rerunning URL recovery checks its saved URL rather than recreating
the original PDF identification. Selected-paper lookups rerun identification
using the current server-side configuration.

- `RELINK_HISTORY_ENABLED=0` disables reading/writing the disk history in the UI.
  It does not delete an existing history file.
- `RELINK_HISTORY_MODE=oidc` is the default; `local` is an explicit single-operator
  exception. Invalid modes fail closed. Native OIDC requires an unexpired token.
- `RELINK_HISTORY_PATH=/absolute/private/path/history.json` overrides the base.
  Private mode uses sibling `history-users/<namespace>.json`; local mode uses the
  exact file. This is trusted configuration, never an input-supplied storage path.
- Keep up to **50** newest entries, **2 MiB per entry**, **10 MiB for the file**.
  The oldest entries are pruned as needed. Results too large for history remain
  viewable in the app with an explicit not-saved warning.

The store uses versioned JSON, declared dataclass schemas, bounded reads, a
process-wide thread lock, fsync, and atomic replacement. It never uses pickle or
user-supplied type names. Malformed/incompatible history is reported without
silently replacing it; searching still works. Explicit Clear saved history can
reset the file. A failed write leaves the previous file intact and current/new
results remain viewable.

Use one app process per history file. Multiple independent writers/processes and
cloud deployments that erase local disks are outside this local-store guarantee.
Back up the file or export history before moving/deleting the workspace. No
database or password system was added. Native Streamlit OIDC uses an external
identity provider and the official auth dependency extra. Existing JSON storage
bounds apply independently per account; the server operator still controls files.

## Verification

Latest complete run: **173 tests and 142 subtests passed**, no skips/failures.
See [history-isolation-pytest.log](readiness/history-isolation-pytest.log) and
[JUnit](readiness/history-isolation-pytest.xml).

Tests use temporary history paths and mocked service responses; no test fixture
is written to the real local workspace history. A separate Python process reads
a saved entry; a fresh Streamlit AppTest session reopens it without providers.
Tests also cover retention, deletion, permissions, concurrent session threads,
corrupt/oversized data, atomic write failure, disabled history, explicit reruns,
and preserving oversized/unsaved rerun results. Browser visual acceptance remains
pending; no live provider requests were needed to test disk persistence.
New isolation tests cover two accounts, guest denial, legacy-file separation,
stable identity across fresh sessions, current-account-only exports/deletes/clears,
stale handles/fragments and identity changes during successful/failed requests.
Actual OAuth redirects/cookies and browser Blob downloads require a configured
provider/manual browser test; they are not established by mocked AppTest results.
