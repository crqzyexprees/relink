# Code, UI, and reliability review improvements

Scope: owner's full review request. Preserve both workflows and existing user
work; make targeted fixes rather than a frontend rewrite or provider expansion.

- [x] Reproduce and fix cross-host TLS connection reuse caused by IP-pinned pool
  origins. Preserve public-address checks and independent hostname verification.
- [x] Add cooperative elapsed-budget checkpoints in addition to inactivity/byte/
  redirect limits. Test body streaming/redirects with fake clocks. Strict header
  read cancellation remains open, with a saved deterministic reproduction.
- [x] Canonicalize safe escaped path characters without conflating reserved
  separators, query strings, dot-segment spellings, or non-root trailing slashes.
- [x] Reduce prefix-induced identity false positives and avoid repeated text
  tokenization, while preserving partial title retrieval support.
- [x] Exclude the selected paper's own DOI aliases from dataset link choices;
  classify deeply nested malformed JSON as provider failure.
- [x] Keep action errors visible across reruns, clear them on relevant input
  changes, shorten UI explanations, and progressively reveal long abstracts.
- [x] Run regressions and complete suite; perform bounded live checks where
  helpful, save actual evidence, and update STATUS/README/review findings.

Reviewers: independent read-only provider/network review plus coordinator UI/state
review. Release source publication, real-browser appearance, and native PDF parse
wall-clock isolation remain explicit limitations; no compliance clearance inferred.
