# PyMuPDF licensing decision for ReLink

Reviewed: 2026-10-24. Decision: **AGPL-3.0-only open-source release**, authorized
by the project owner after the initial review. This records a
technical compliance review, not legal clearance or a license grant for ReLink.

## What was checked

- The working environment uses PyMuPDF 1.28.2. `relink/extraction.py` imports it
  directly for PDF text, annotations, and contextual clipping in the same app.
- Added the full AGPLv3 LICENSE, NOTICE, README license declaration, and visible
  Streamlit license/source information. Original code uses AGPL-3.0-only;
  dependencies retain their own licenses. No parser replacement is needed.
- Public project source was published on 2026-10-25 at
  https://github.com/crqzyexprees/relink. The remote is configured and an anonymous
  source-file request returned HTTP 200. The app reads RELINK_SOURCE_URL and
  displays its configured public source link; set it to the exact deployed
  commit before hosting. Missing/unsafe values produce a deployment warning.
- Installed PyMuPDF `COPYING` contains only a dual-license summary. It is not the
  full AGPL text. The version-specific upstream
  [COPYING](https://github.com/pymupdf/PyMuPDF/blob/1.28.2/COPYING) contains AGPLv3.
- [Artifex's current licensing guidance](https://artifex.com/licensing) explicitly
  requires application source disclosure under AGPL for its AGPL server-based
  integrations; it offers commercial terms for uses that cannot comply.

AGPL section 13 addresses remote users of a modified covered program. Whether a
particular integration forms a covered combined work is a legal scope question;
this review follows the vendor's published position for ReLink's direct library
integration. Unrelated independent software is not automatically relicensed.

## Routes considered in the initial review

| Route | What it means for ReLink | Remaining work |
| --- | --- | --- |
| AGPL compliance | Keep PyMuPDF and make the covered application source available to its users under applicable AGPL terms. | Team approval, license/notices, corresponding source, and visible source offer. |
| Artifex commercial agreement | Keep PyMuPDF with permissions defined by that agreement. | Obtain and review written terms covering this product and deployment/distribution. |
| Replace PyMuPDF | Remove this dependency and its bundled MuPDF from the release. | Approve a stack change, migrate PDF extraction and fixtures, audit dependencies, rerun acceptance. |

For a team comfortable releasing the application under AGPL, that route needs
the least code change. A proprietary product does not have to buy a license if
it instead removes the dependency and uses a suitable alternative.

## Checklist for the AGPL route

The owner selected open source. Remaining release tasks still require verification.

- [ ] Confirm the team's rights to license all contributed code and identify
  copyright owners. Review copied code and other dependencies for compatibility.
- [x] Select the project's license explicitly, add its full unmodified text,
  and document the choice and copyright/notices in the README.
- [ ] Prepare corresponding source for the exact deployed version, including
  required install/run/build scripts and necessary dependency source material.
  Review AGPL sections 1, 4–6, and 13 against the actual deployment artifact.
- [x] Provide a prominent Source / License entry in Streamlit with the applicable
  legal and warranty notices. A public repository with a deployed-version tag
  and source download is a practical implementation; GitHub is not mandatory.
  The UI is implemented; its real source destination still needs configuration.
- [x] Verify an ordinary user can access the published project source without charge. A
  private repository inaccessible to users or a repository without a license
  does not complete these tasks.
- [ ] Preserve upstream copyrights, license texts, and applicable NOTICE files.
  If shipping a container or bundled environment, review its included native
  libraries and covered binary/source obligations too. A pip requirements file
  alone is not a complete redistribution compliance package.
- [ ] Repeat the source/version and notice checks whenever deploying an update.

Do not publish credentials, uploaded papers, or dataset files as part of this
software source task. Those materials have separate rights; reading a PDF does
not automatically relicense it under AGPL. ReLink currently reads PDFs rather
than creating or modifying them, so the vendor's PDF producer-line guidance is
not a reason to alter uploaded papers.

## Checklist for a commercial inquiry

Prepare these details for Artifex before requesting a quote:

- ReLink, PyMuPDF 1.28.2 / bundled MuPDF, Python/Streamlit, read-only PDF link and
  text extraction; identify the team or legal entity holding the license.
- Intended use: local demonstration, public hosted service, and/or distributing
  source, installers, wheels, or containers; expected users and deployments.
- Requested coverage for development and production, hosting/distribution scope,
  duration, renewal costs, and any reporting or notice obligations.

Require written terms covering the actual use before treating this route as
resolved. No quote, fixed price, student exception, or existing commercial
permission was established. Charging money alone is not what determines whether
the commercial route is needed: AGPL itself permits commercial use subject to
its conditions. No vendor contact or purchase was made during this review.

## Replacement option

[pypdf documents its BSD-3-Clause license](https://pypdf.readthedocs.io/en/latest/meta/faq.html#which-license-does-pypdf-use).
It is a candidate for a permissively licensed parser, not a validated drop-in
replacement. A migration must check text and annotation URLs, surrounding context,
wrapped links, encrypted/malformed PDFs, resource limits, and the real SQuAD
paper-to-recovery flow. Remove PyMuPDF-dependent test fixtures as well as runtime
imports and verify the shipped environment no longer includes it. Retain pypdf's
own notices and review the final dependency tree.

The owner subsequently authorized the open-source changes and GitHub publication.
The public repository is now accessible. No commercial purchase, vendor contact
or parser migration was performed. Confirm contributor rights, pin/configure the deployed source URL,
and complete the applicable release-artifact checks before public deployment.
