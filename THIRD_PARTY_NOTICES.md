# Third-party dependencies and attribution review

Reviewed 2026-10-24 against the installed environment. This is a dependency review,
not a project license grant, complete redistribution bundle, or compliance clearance.

| Direct dependency | Installed | License recorded upstream | Handling |
| --- | --- | --- | --- |
| [Streamlit](https://github.com/streamlit/streamlit) | 1.66.1 | Apache-2.0 | Preserve license/copyright notices and any applicable NOTICE when redistributing; identify modifications where required. |
| [HTTPX](https://github.com/encode/httpx) | 0.28.1 | BSD-3-Clause | Retain upstream copyright, conditions, and disclaimer; do not imply endorsement. |
| [PyMuPDF / MuPDF](https://artifex.com/licensing) | 1.28.2 | AGPLv3 or Artifex commercial license | Resolve the AGPL/source-disclosure route or obtain an applicable commercial license before public deployment/distribution. Attribution alone does not settle this. |
| [pytest](https://github.com/pytest-dev/pytest) | 9.1.1 | MIT | Retain license/copyright notice if redistributed; used for development/tests. |

## Open-source route selected; deployment checks remain

The owner selected AGPL-3.0-only for ReLink's original application code. The
repository now includes LICENSE, NOTICE, and a visible application license/source
entry. Set RELINK_SOURCE_URL to accessible corresponding source for the exact
deployed release. [Public project source](https://github.com/crqzyexprees/relink)
was published on 2026-10-25 and an anonymous source-file request returned HTTP 200.
Artifex's [licensing guidance](https://artifex.com/licensing)
states that its AGPL server use requires disclosure of the application's source
under AGPL, and directs uses that cannot comply to commercial licensing.
The AGPL route still needs deployed-version source-link and release-artifact checks. See the version-specific
[full AGPL text](https://github.com/pymupdf/PyMuPDF/blob/1.28.2/COPYING).
The installed PyMuPDF 1.28.2 `COPYING` file contains only a dual-license summary,
not the full license. Public release clearance is **BLOCKED pending those checks**. The repository
assessment, three available routes, and concrete release checklists are in
[docs/LICENSING.md](docs/LICENSING.md).

The repository imports these packages; `.venv` and uploaded/downloaded PDFs are
not committed. When shipping a bundled environment/container, retain actual
upstream license/NOTICE files rather than relying on this summary. The installed
Streamlit metadata did not expose a license file in its distribution directory;
obtain the upstream LICENSE/NOTICE material for any redistribution bundle.

## Transitive dependencies

The subsequent private-history feature enables Streamlit's supported `[auth]`
extra. The approved installation added these packages; exact installed license
metadata, upstream URLs and license-file hashes are in
[auth-dependencies.json](docs/readiness/auth-dependencies.json), with
[installation output](docs/readiness/auth-install.log):

| Authentication dependency | Installed | Recorded license |
| --- | --- | --- |
| Authlib | 1.9.1 | BSD-3-Clause |
| joserfc | 1.7.7 | BSD-3-Clause |
| cryptography | 50.0.2 | Apache-2.0 OR BSD-3-Clause |
| cffi | 2.1.1 | MIT-0 |
| pycparser | 3.12 | BSD-3-Clause |

Retain their own and bundled native-library notices when redistributing an
environment. This is an incremental inventory, not a new comprehensive audit.
OIDC provider service terms remain separate from these package licenses; no
provider account/application, subscription or deployment was created. Auth0 and
Google credentials are supplied by the operator, not bundled with ReLink.

[The inventory](docs/readiness/dependencies.json) records the 42 active installed
Python runtime/test dependencies reachable from requirements.txt: exact versions,
declared license metadata, upstream links, and SHA-256 hashes of discovered
license files. It excludes inactive extras and is not a dependency lockfile.

Important categories include Apache-2.0, BSD, MIT, PSF-style licenses, NumPy's
composite notices, and certifi's MPL-2.0. Preserve each package's own terms when
redistributing. Some packages have missing/ambiguous license-expression metadata
(for example Jinja2, itsdangerous, and python-dateutil); inspect their bundled
license files, which are identified in the inventory, instead of treating an
empty metadata field as permission. This inventory does not enumerate every
vendored JavaScript/native library/font inside upstream wheels; preserve their
bundled notices too. No comprehensive vulnerability audit or commercial-license
validation was performed.

The [PyMuPDF changelog](https://pymupdf.readthedocs.io/en/latest/changes.html)
also lists PDF text-extraction hangs affecting 1.28.x among fixes for 2.0. ReLink's
input limits do not impose a wall-clock deadline inside native `get_text` calls.
Use preflighted papers for the demo. A parser upgrade or process-isolation review
is needed before accepting arbitrary untrusted public uploads. A major parser
upgrade was not part of these targeted demo fixes and requires separate acceptance.

## Data sources and demonstration material

- Gemini is now a core external service for paper/PDF dataset identification,
  accessed with HTTPX; no Google SDK was added. The server sends bounded text
  excerpts on explicit Find, disclosed before action. Use public/nonconfidential
  papers and review [Gemini API terms](https://ai.google.dev/gemini-api/terms) and
  [pricing/data use](https://ai.google.dev/gemini-api/docs/pricing). The default
  model is free-tier eligible; actual project billing/quota and data handling
  remain Google's terms, not the application's AGPL license. No billing upgrade
  was authorized or performed. Locally checked short source excerpts retain the
  paper's rights and page/source attribution; no PDF is bundled or relicensed.
  Model output does not establish dataset provenance, usage or identity.

- [OpenAlex metadata](https://github.com/ourresearch/openalex-docs/blob/main/license.md)
  is offered under CC0. ReLink retains work IDs, DOIs, retrieval timestamps, and
  original source links. Abstracts and downloaded PDFs may carry third-party
  rights; the application license does not relicense them. The app downloads
  at most one advertised public paper PDF in memory on explicit action and does
  not redistribute PDF files or bypass access restrictions. Observe the public
  API's quota/rate limits; no paid API key or paid LLM was added.
- [DataCite metadata](https://support.datacite.org/docs/harvesting-datacite-doi-metadata)
  is offered under CC0. ReLink nevertheless retains DOI/source provenance and
  requests `rightsList`. Metadata reuse does not grant rights to the linked
  dataset files; inspect the actual resource license and attribution requirements.
- Internet Archive results identify archived content, whose copyright and dataset
  licenses remain separate from API access. A capture is not permission to reuse
  a dataset. ReLink reports links and does not download or redistribute dataset bytes.
- The proposed public paper is Rajpurkar, Zhang, Lopyrev, and Liang (2016),
  *SQuAD: 100,000+ Questions for Machine Comprehension of Text*,
  [arXiv:1606.05250](https://arxiv.org/abs/1606.05250). Its PDF is not bundled.
- The DOI demo input is Fisher's [Iris dataset at UCI](https://archive.ics.uci.edu/dataset/53/iris),
  DOI `10.24432/C56C76`. UCI lists CC BY 4.0 for that dataset. Cite its authors and
  repository if using the data; this demo searches metadata and claims no byte recovery.
