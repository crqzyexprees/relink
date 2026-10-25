# Real examples to try in ReLink

Live check started **2026-10-25 00:16:35 UTC** (October 24 in America/New_York).
Follow-up at **03:29:28 UTC** fixed the escaped-path rejection for CIFAR and the
Iris/Irish prefix-ranking error. The original observations below remain historical;
see [review-live.json](readiness/review-live.json) and [REVIEW.md](REVIEW.md) for
current evidence. CIFAR now returns its reported capture, and the unrelated marine
record remains unverified below true Iris results.
These are actual engine/service results, not mocked responses or promised future
outcomes. Evidence: [real-examples.json](readiness/real-examples.json).
The first sandbox attempt had DNS failures; the approved host execution produced
the results below. No dataset payloads were downloaded or hashes verified.

## Paste these into Recover URL

| Example and input | Observed original URL | Actual discovery | What to demonstrate |
| --- | --- | --- | --- |
| MNIST training images: `http://yann.lecun.com/exdb/mnist/train-images-idx3-ubyte.gz` | HTTP 404 | One Archive candidate, capture `20260225205805`; DataCite empty | Best broken-file-link example. The API reports a capture; replay and file bytes are unverified. |
| SQuAD: `https://stanford-qa.com` | ConnectError; no HTTP status | One Archive candidate, capture `20250407122419`; DataCite empty | Recovery lookup can return a lead despite an unreachable original. This was not an observed 404. |
| Iris DOI: `https://doi.org/10.24432/C56C76` | Redirects to UCI, HTTP 200 | One DataCite record, DOI `10.24432/c56c76`, repository `https://archive.ics.uci.edu/dataset/53`; Archive empty | Reliable repository identity search. This is a working DOI, not a broken-link recovery. |
| Wisconsin diagnostic DOI: `https://doi.org/10.24432/C5DW2B` | Redirects to UCI, HTTP 200 | One DataCite record, DOI `10.24432/c5dw2b`, repository `https://archive.ics.uci.edu/dataset/17`; Archive empty | Second independent dataset/DOI example; metadata remains unverified content. |
| Old Iris page: `https://archive.ics.uci.edu/ml/datasets/iris` | Redirects to current Iris page, HTTP 200 | One Archive candidate, capture `20230527023034`; DataCite empty | A moved URL can still work through redirects. |
| Old Wisconsin page: `https://archive.ics.uci.edu/ml/datasets/Breast+Cancer+Wisconsin+(Diagnostic)` | Redirects to current dataset page, HTTP 200 | One Archive candidate, capture `20230606194802`; DataCite empty | Redirect handling and historical page evidence. |
| CIFAR-10: `https://www.cs.toronto.edu/~kriz/cifar.html` | Redirects to `https://cave.cs.toronto.edu/kriz/cifar.html`, HTTP 200 | Archive `invalid_response`; DataCite empty; no candidate accepted | An honest integration limitation, not a successful recovery or a successful empty search. |

All six returned URL/DOI candidates were ranked `likely_match`, not verified exact
matches. Every Archive candidate remains `archive_metadata_only`. A reported
capture can itself be an error page; it proves neither replay access nor preserved
downloadable dataset bytes. Current checks inspect HTTP status, not payload identity.

## Why these inputs are real

- The historical MNIST URL is listed in the upstream
  [torchvision v0.8.2 MNIST implementation](https://github.com/pytorch/vision/blob/v0.8.2/torchvision/datasets/mnist.py).
  Its historical MD5 is not a verification performed by ReLink.
- The [SQuAD paper](https://arxiv.org/abs/1606.05250) explicitly points to
  stanford-qa.com. Its [project page](https://rajpurkar.github.io/SQuAD-explorer/)
  provides further human context; it is not an engine-discovered fallback.
- UCI provides the authoritative [Iris citation/DOI](https://archive.ics.uci.edu/dataset/53/iris)
  and [Wisconsin diagnostic citation/DOI](https://archive.ics.uci.edu/dataset/17/breast+cancer+wisconsin+diagnostic).
  The old URL routes redirected to those current pages during the live check.
- The [CIFAR project page](https://www.cs.toronto.edu/~kriz/cifar.html) redirects
  to its current host. A follow-up real Archive API response encoded `~` as `%7E`
  in the capture target. ReLink's strict identity comparison rejected it. The
  response is saved in [cifar-availability.json](readiness/cifar-availability.json).
  Safe normalization of unreserved characters is a follow-up improvement;
  do not disable target validation merely to accept this example.

## PDF demonstration

Download the actual [SQuAD paper PDF](https://arxiv.org/pdf/1606.05250), upload it
under Analyze PDF, and select `https://stanford-qa.com`. Clear optional context to
reproduce the URL-only query above. The previous live paper acceptance parsed
10 pages and three web links; see [host-live-checks.json](readiness/host-live-checks.json).
This evaluation reran URL recovery; it did not repeat the live PDF download.

## Optional metadata-only CLI search

```bash
.venv/bin/python -m scripts.discover_datasets --title Iris --author Fisher
.venv/bin/python -m scripts.discover_datasets --doi 10.24432/C56C76
.venv/bin/python -m scripts.recover_url 'http://yann.lecun.com/exdb/mnist/train-images-idx3-ubyte.gz'
```

The actual Iris/Fisher search returned five records, including the UCI Iris record,
two Figshare DOI versions, another Iris record, and an unrelated marine-monitoring
record. The latter received likely_match from lexical signals: a known relevance
limitation. Distinct DOI versions remain separate. Prefer DOI search for the main
demo; manually inspect all keyword-search candidates. No ranking score is a
calibrated probability or independent identity verification.

## Coverage and limitations

These cases were selected for recognizable provenance and distinct behaviors,
not a statistical recovery-rate estimate. One file URL actually returned 404;
another dataset host was unreachable; the others were working controls/redirects.
This does not finish the planned benchmark of five real broken dataset links.
Provider availability and captures can change. Recheck before presenting, inspect
source checks, and export the actual JSON report. These inputs and saved reports
are evaluation material only and are never loaded as live app results.
