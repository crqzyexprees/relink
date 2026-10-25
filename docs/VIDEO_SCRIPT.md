# ReLink submission video — three real demonstrations

Target: about 4 minutes 30 seconds, below the event's stated five-minute maximum.
This is a screen-recording script, not a generated video. Replace [your name].
The spoken text below is a suggested narration; describe the actual screen when
live outcomes differ. Shorten waits with an obvious edit, never invented results.

## Inputs to prepare

| Demo | Exact input | Checked outcome, 2026-10-25 UTC |
| --- | --- | --- |
| Paper with an unreachable dataset address | Upload SQuAD PDF and choose `https://stanford-qa.com` | Actual paper: 10 pages; URL connection failure, not 404. Archive API returned capture 2025-04-07 12:24:19 UTC. Combined uploaded-PDF lookup retained it as likely_match. |
| Find a paper and follow its dataset source | Find papers: `palmerpenguins` | 13 papers ranked; intended R Journal paper was first in this run. Its 11-page PDF was parsed. Paper-extracted author dataset website returned HTTP 200. Rank/order may change. |
| Find a repository dataset by DOI | Find datasets → Search datasets: `10.24432/C56C76` | Actual UCI Iris DataCite record; dataset AI ranked; likely_match, no independent file verification. |

Public paper sources:

- SQuAD: [paper](https://arxiv.org/abs/1606.05250),
  [PDF](https://arxiv.org/pdf/1606.05250).
- Palmer Archipelago Penguins Data in the palmerpenguins R Package - An
  Alternative to Anderson's Irises:
  [article](https://journal.r-project.org/articles/RJ-2022-020/),
  [PDF](https://journal.r-project.org/articles/RJ-2022-020/RJ-2022-020.pdf).
- [Author-linked penguin dataset website](https://allisonhorst.github.io/palmerpenguins/),
  [its data download instructions](https://allisonhorst.github.io/palmerpenguins/articles/download.html).
- [UCI Iris dataset](https://archive.ics.uci.edu/dataset/53/iris).

Downloaded original PDFs are available locally under the ignored
`.relink/demo-inputs/SQuAD-2016.pdf` and
`.relink/demo-inputs/palmerpenguins-2022.pdf`. They are not committed.
Fresh engine/service observations are in
[video-demo-live.json](readiness/video-demo-live.json). These are local live
checks, not fresh hosted UI acceptance. No recovery results are loaded into
production from that file.

## 0:00–0:25 — Problem and introduction

Screen: ReLink with the two search tabs visible. Keep credentials and unrelated
browser tabs outside the recording.

Say:

> Hi, I'm [your name], and this is ReLink. A research paper can stay online while
> its dataset link disappears. That makes reproducing the work much harder.
> ReLink helps you find relevant papers, investigate their dataset links, and
> compare surviving sources using evidence you can inspect. I'll show three
> real examples.

## 0:25–1:35 — An old paper with an unreachable dataset URL

Actions:

1. Open Find datasets → Analyze PDF.
2. Upload SQuAD-2016.pdf.
3. In Choose a research link, select `https://stanford-qa.com`.
4. Show the extracted surrounding text. Click Find once.
5. Show Original URL status and the Internet Archive candidate. Its recorded
   capture timestamp was 20250407122419; use whatever the real response shows.

Say while selecting the paper/link:

> This is the original SQuAD paper, a well-known question-answering dataset.
> ReLink extracts its research links and nearby text, so I can investigate the
> address printed in the paper without manually copying it.

Say when actual results appear:

> In this check, the original address could not be reached. ReLink still found a
> capture reported by Internet Archive and shows its date and matching evidence.
> It labels this as a likely match. An archived page is a useful lead, but
> preserved dataset files still need to be checked.

Do not call the connection failure a 404. Gemini identification was partial in
the preflight and also found background-mentioned datasets. Do not describe all
such mentions or loosely related repository candidates as the paper's own data.
Do not claim archive replay or dataset bytes were successfully downloaded.

## 1:35–3:05 — Discover a paper and reach its real dataset source

Actions:

1. Open Find papers. Enter `palmerpenguins`. Click Find papers once.
2. Choose the paper whose title begins Palmer Archipelago Penguins Data in the
   palmerpenguins R Package. Select by title, not a promised rank.
3. Briefly show its abstract, Gemini explanation and supporting source passage.
4. Click Find datasets from this paper.
5. Scroll to Dataset evidence from the selected paper. Under Research link to
   check for dataset copies, select
   `https://allisonhorst.github.io/palmerpenguins/`.
6. Click Find copies of selected link. Show the working original URL and click
   Open original source. On the author's site, show About the data or
   Extras → Download the data directly. Return to ReLink afterward.

Say during paper discovery:

> Now I'm looking for papers about the Palmer penguin data. ReLink searches
> scholarly sources and ranks the available abstracts with Gemini. This result
> explains the dataset and links to its authors' data resources. The ranking
> includes a passage from the actual abstract, so I can inspect the support.

Say during dataset investigation:

> I can continue directly from the paper to its dataset evidence. Repository
> records can be loosely related, so here I'm selecting the authors' dataset
> website extracted from the paper. ReLink checks the address, and the original
> source is working. Opening it brings me to the data documentation and download
> instructions. That connects finding a paper with locating its data source.

The preflight returned 13 combined repository candidates, including unrelated
penguin tracking/drone records. Those are unverified leads; do not claim the
first repository candidate is the dataset used by this paper. The successful
route demonstrated here is the actual author link extracted from the PDF.
The author site opens in a separate browser tab; switch to it manually.

## 3:05–3:50 — Dataset identity and an exportable evidence report

Actions:

1. Open Find datasets → Search datasets.
2. Enter `10.24432/C56C76`. Click Find once.
3. Show the Iris candidate, original DataCite source, DOI, ranking explanation,
   Dataset AI status and likely-match label.
4. Click Download evidence report (.json). It is also fine just to show the
   button if browser download dialogs would interrupt the video.

Say:

> For the third example, I have a known dataset DOI. ReLink finds the Iris record
> in DataCite and retains its UCI repository address. The result explains its
> matching evidence and AI-assisted relevance assessment. I can export a JSON
> report containing the query, source checks, results and evidence. This gives
> another researcher a structured record of what I found and what remains
> unverified.

This is a working-dataset metadata lookup, not recovery of a broken link. The
JSON contains evidence, not dataset files. Previews appear only for supported,
actually advertised CSV/TSV files; do not promise a preview on this Iris record.

## 3:50–4:25 — Implementation and close

Screen: return to the app and optionally open License & source/GitHub.

Say:

> ReLink is built in Python with Streamlit, PyMuPDF and httpx. OpenAlex and arXiv
> provide paper records, Internet Archive supplies capture leads, and DataCite
> supplies repository metadata. Gemini assists relevance ranking while the
> original sources and verification labels remain visible.
>
> Next, I want to expand repository coverage and strengthen dataset-version and
> file verification. ReLink is open source, and its goal is to make the path
> from a research idea to inspectable data easier to follow.

## Recording checklist and fallback

- Rehearse these exact inputs once in the hosted app. Search order, provider
  availability and model assessments can change. Show actual statuses.
- Record at 1080p or higher with readable browser zoom. Keep the cursor steady;
  show the result and its evidence rather than scrolling every record.
- Leave out Auth0/private-history claims until a real login and account isolation
  have been demonstrated. Never record Streamlit Secrets or Auth0 credentials.
- If a wait is lengthy, use a short jump cut labeled Search wait shortened. Keep
  original footage; do not edit an error into a successful outcome.
- For a backup broken-file case, use Find datasets → Recover URL:
  `http://yann.lecun.com/exdb/mnist/train-images-idx3-ubyte.gz`.
  Actual preflight: 404 plus an Archive capture 20260225205805. It is a genuine
  historical dataset URL, but not the URL extracted from the SQuAD paper.
- If live services fail, label the failure or retry after their stated interval.
  A previously recorded genuine run may be shown with its date; do not present
  mocked tests or saved preflight JSON as newly returned live app results.
- The event listing requests a maximum five-minute video:
  [HackPSU Fall 2026 requirements](https://hackpsu-fall-2026.devpost.com/).
