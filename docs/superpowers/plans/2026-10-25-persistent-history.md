# Persistent local search history

Owner scope: preserve history after browser closure/app restart for both tabs,
without a database or accounts. This is local workspace history on the machine
running ReLink, shared by users of that workspace, not private per-browser storage.

- [x] Write failing persistence/validation/retention tests. Add history.py with a
  versioned JSON store, atomic file replacement, private file permissions, and
  safe reconstruction of explicitly allowed result dataclasses. No pickle.
- [x] Bound to 50 entries, 2 MiB per entry, 10 MiB total; prune oldest entries.
  Preserve failed/empty provider outcomes and timestamps. Never store PDF bytes.
  Corrupt/unwritable history must not break search or be silently overwritten.
- [x] Add a history sidebar and dated snapshot viewer. View/export/delete/clear
  never invoke providers. Search again is explicit and creates a new dated entry.
  Cover URL recovery, paper searches and paper-dataset lookups. Export is supported;
  arbitrary history-file import and account/browser storage are deferred.
- [x] Save only on completed explicit actions. Isolate test history paths and prove
  a new app session can reopen results without requests. Verify reruns do not add
  duplicates, saved failures stay failures, and storage failure preserves results.
- [x] Run full tests, update README/STATUS/.gitignore/environment example. Review
  privacy and validation; do not publish or commit local search data.

Default path: .relink/history.json under project root, configurable by trusted
RELINK_HISTORY_PATH. RELINK_HISTORY_ENABLED=0 disables disk history for public/
shared deployment. Sidebar explicitly describes local shared storage. No live
network calls are needed to verify persistence or snapshot restoration.
