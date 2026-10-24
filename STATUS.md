# ReLink status

Updated: 2026-10-24.

## Progress

- M0: scaffold complete; HTTPX is usable through a local dependency workaround.
  Full requirements installation remains blocked by network restrictions.
- Authorized URL recovery slice: implemented, with 26 passing offline tests.
  Includes current access checks, public-address protection, the Internet Archive
  availability adapter, shared result models, orchestration, and CLI.
- M2: provider implementation and offline checks complete; successful live service
  behavior remains unverified.
- M1: URL validation and URL recovery contracts implemented; PDF/context extraction
  and full paper models remain deferred.
- M3/M4: only single-provider orchestration and current URL status checks were
  authorized here. DataCite, ranking, and dataset verification remain deferred.
- M5/M6: frontend and real broken-dataset evaluation not started.

## What works in mocked tests

- Current URL status distinguishes working 2xx, 404, 403, 429, other HTTP errors,
  DNS failure, timeout, connection errors, blocked targets, and redirect errors.
- Redirects retain final URL and history; current checks do not read bodies.
- Archive candidates preserve original URL, reported replay URL, capture timestamp,
  source, retrieval time, evidence, and archive_metadata_only verification.
- Empty/unavailable capture responses return not-found. Malformed responses,
  inconsistent replay metadata, HTTP errors, DNS failures, timeouts, and rate
  limits remain failures with no invented candidates.
- Public-only transport rejects non-public literals and DNS answers, including
  mixed answers. Connections are pinned to validated IPs while retaining Host and
  TLS server name. Redirects get the same checks; HTTPS downgrades are blocked.
- DNS/HTTP timeouts, five redirects maximum, a 1 MiB API body limit, and no automatic
  retries bound requests. Rate-limit responses expose Retry-After.
- CLI prints JSON and uses exit codes 0 for completed archive lookups, 1 for failed
  or blocked lookups, and 2 for invalid or unsafe input.

## Decisions

- Python 3.12.15, root-level relink package, and separate CLI demo.
- Keep network policy, status checking, provider access, and orchestration separate.
  A provider protocol leaves room for future adapters without UI dependencies.
- Tests use unittest TestCase, which pytest can collect. The standard runner is
  available in this restricted environment. HTTP and DNS are always mocked.
- Standard HTTP/HTTPS ports only; no credentials, internal names, unsafe redirects,
  environment proxies, or compressed API responses. See README.md for policy.
- Validate replay host, embedded target, and timestamp consistency. Strict target
  matching can reject a capture for a canonicalized alternate URL; searching
  alternate URLs is future work.
- A working URL still gets an archive lookup. Current DNS/timeout errors do not
  suppress lookup; a blocked current check does suppress forwarding the target.
- No capture replay, file downloads, dataset identity checks, frontend, PDF
  extraction, ranking, or additional providers were implemented in this slice.

## Environment and Git

- An empty, read-only .git directory exists. Plain git init fails with “Read-only
  file system”; plain git status remains unusable.
- Initialized a fresh repository in .git-local. Use
  `git --git-dir=.git-local --work-tree=. status`. This works; metadata is ignored.
  No commits or staging were performed.
- Normal pip installation was retried before implementation and failed. DNS cannot
  resolve pypi.org; direct curl also failed with “Operation not permitted”. No
  permission escalation was attempted.
- Copied installed pure-Python system distributions and metadata into the venv:
  HTTPX 0.28.1, httpcore 1.0.9, h11 0.16.0, certifi 2026.1.4, anyio 4.13.0,
  idna 3.18, and typing_extensions 4.16.0. HTTPX imports and pip check pass.
  This is a local workaround; normal installation remains the supported setup.
- Pytest, Streamlit, and PyMuPDF remain unavailable. requirements.txt still declares
  the intended stack with major-version bounds; there is no lockfile.

## Verification evidence — URL feature

- `.venv/bin/python -m unittest discover -s tests -v`: 26 tests passed. All HTTP and
  DNS responses are mocked. Coverage includes IPv6 site-local addresses, mixed DNS
  answers, unsafe redirects, connection pinning, DNS timeout, and streamed limits.
- `.venv/bin/python -m pytest -q`: could not run, No module named pytest. Do not
  report the standard runner's results as a successful pytest execution.
- `.venv/bin/python -m compileall -q app.py relink scripts tests`: passed.
- `.venv/bin/python -m pip check`: passed for the locally copied distributions;
  this does not establish that all declared requirements are installed.
- Live CLI: `.venv/bin/python -m scripts.recover_url https://www.psu.edu/` exited 1
  with current.status=dns_failure, archive.status=dns_failure, and no candidate.
  Neither an HTTP status nor archive availability could be established.
- A separate unmocked invocation recorded the same outcome at
  2026-10-24T21:11:48.194772+00:00 in docs/live-url-check.json.
- The external web tool also could not fetch the availability query. This adds no
  evidence about actual capture availability.

## Blockers and unverified behavior

- Successful live API responses, replay accessibility, and real TLS/network behavior
  remain unverified while outbound DNS/network access is blocked.
- Pytest collection/execution awaits installation. Normal full dependency setup
  and a standard writable .git directory await host access.
- DNS timeout bounds caller waiting, but OS lookup may continue in a daemon thread.
  HTTP timeouts are per operation. Only the first vetted DNS address is used;
  address-family failover is not implemented.
- No downloadable dataset preservation or recovery success has been verified.

## Next steps

1. On a network-enabled host, install requirements, run pytest, and rerun the CLI
   against a public research dataset URL. Record live responses separately.
2. Restore a writable standard .git directory on the host if ordinary Git commands
   are desired. The explicit .git-local repository is usable now.
3. Continue with PDF/context extraction or another PLAN.md milestone when
   authorized; update this file after each milestone.

## Earlier milestone — M0

The initial scaffold had eight docstring-only Python files, no tests, and no
installed application dependencies. Syntax and package import checks passed.
That scaffold-only state has been superseded by the URL feature above.
