# ReLink

Paper-aware dataset recovery for HackPSU 2026. The first feature checks a public
URL and searches Internet Archive for a reported capture. PDF extraction,
DataCite, ranking, and the Streamlit UI remain planned. See [PLAN.md](PLAN.md),
[STATUS.md](STATUS.md), and [AGENTS.md](AGENTS.md).

## Setup

Python 3.12 is the initial verification target.

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pip check
```

External DNS/network access is blocked in this workspace. HTTPX 0.28.1 and its
pure-Python dependencies were copied from local system packages into `.venv`;
imports and `pip check` pass. Pytest, Streamlit, and PyMuPDF remain unavailable.
On a network-enabled machine, install requirements normally. The local copy is
an environment workaround, not a lockfile. Requirements have major-version bounds.

## CLI demo

```bash
.venv/bin/python -m scripts.recover_url 'https://www.psu.edu/'
```

JSON output contains `original_url`, `current`, and `archive`. Current status
separates `working`, `not_found` (404), `forbidden` (403), `rate_limited` (429),
`dns_failure`, `timeout`, `blocked`, `redirect_error`, `http_error`, and
`network_error`. Final URL, redirect history, and HTTP status are included.

The [Internet Archive availability API](https://archive.org/help/wayback_api.php)
adapter can return a `found` candidate with original URL, archived URL, capture
timestamp, source, retrieval time, and evidence. Other outcomes are `not_found`,
`rate_limited`, `timeout`, `dns_failure`, `blocked`, `error`, or `invalid_response`.
An API failure never becomes a not-found result.

Every candidate is `archive_metadata_only`: replay accessibility and downloadable
dataset preservation have not been checked. Replay host, embedded original URL,
and capture timestamp must agree before a candidate is accepted. The lookup uses
the original URL even if it currently redirects. Working URLs also get a lookup.

Exit codes: `0` for a completed archive search (`found` or `not_found`), `1` for a
blocked/failed lookup, and `2` for invalid or unsafe input. Exit `0` does not claim
that a dataset was recovered.

## Request policy

- Public HTTP/HTTPS addresses on standard ports only. Credentials, internal
  names, non-public IPs, and mixed public/private DNS answers are blocked.
- Connections use a vetted IP with the original Host header and TLS server name,
  preventing a second hostname resolution from rebinding to an internal address.
  Environment proxies are disabled.
- Every redirect gets the same validation. HTTPS downgrades, loops, and missing
  redirect locations are errors. Maximum five redirects per fetch.
- DNS waiting and each HTTP connect/read/write/pool operation have ten-second
  limits. These are per-operation limits, not an end-to-end deadline.
- Current checks use streamed GET requests and close without reading the body.
  API bodies are limited to 1 MiB. Compressed API bodies are rejected.
- No automatic retries. Rate limits expose `Retry-After` for the caller to honor
  before another attempt. Each CLI run makes one recovery attempt.

## Tests and live checks

```bash
.venv/bin/python -m pytest -q
# Equivalent runner when pytest is unavailable:
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m compileall -q app.py relink scripts tests
```

The pytest-compatible unittest suite uses HTTPX MockTransport and mocked DNS.
Unexpected real DNS fails a test. Tests exercise the production validators,
transport, status checks, provider, orchestration, and CLI.

Live checks run separately. The attempt against `https://www.psu.edu/` failed at
DNS before either HTTP service was reached; see [the live record](docs/live-url-check.json).
No live capture or dataset preservation has been verified.

## Git in this workspace

The existing empty `.git` directory is mounted read-only. A fresh repository was
initialized in `.git-local`, which is ignored. Use an explicit metadata path:

```bash
git --git-dir=.git-local --work-tree=. status
```

Plain Git commands remain unavailable until the read-only `.git` mount is
removed on the host. No files have been committed or staged.

## Future UI

After the UI milestone, launch with `.venv/bin/python -m streamlit run app.py`.
The current app.py is a docstring-only placeholder.
