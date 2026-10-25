# History Isolation Implementation Plan

> Execute natively in this workspace using superpowers:executing-plans. Preserve
> unrelated work; do not commit, deploy, register accounts or replace real secrets.

**Goal:** Durable private history with Streamlit OIDC and enforced storage access.
**Architecture:** A small identity/access adapter selects existing bounded JSON
stores; the UI reauthorizes every operation and resets state on identity changes.
**Tech stack:** Python 3.12, Streamlit auth extra, existing JSON store and pytest.
**Spec:** ../specs/2026-10-25-history-isolation-design.md

## Constraints and review focus

- Default OIDC mode; explicit local mode only for a trusted single operator.
- Issuer/subject/expiry from Streamlit, never input/query/email identity.
- No fallback to old shared history for anonymous or invalid identities.
- Fragment/dialog reruns must authorize again, not replay old captured data.
- Reruns must recheck the current identity before persisting/rendering a response.
- Same subject from different providers must remain separate; malformed expiry
  (including booleans/NaN) must fail closed.
- No real login test claims without configured provider credentials/browser.

## Task 1 — Scoped store and identity boundary

- [x] Add failing tests in tests/test_history_isolation.py for two-account CRUD,
  legacy-file isolation, stable restart namespace, different issuer, invalid and
  expired identity, disabled/local/invalid modes and path traversal inputs.
- [x] Add relink/history_access.py: pure resolve_access(mode, enabled, claims,
  now=None), current_access(), store_for_access(access), and session reset helper.
  Hash serialized issuer/subject with SHA-256; validate typed claims and expiry.
- [x] Run focused tests; preserve HistoryStore schema and resource limits.

## Task 2 — Enforce every UI operation

- [x] Add failing native AppTest cases for guest denial, same-user persistence,
  A/B lists/export/delete/clear, stale views/reruns and active state clearing.
- [x] Update history_ui.py record/read/view/rerun/export/delete/clear to require
  the current scope. Saved dialogs reload by ID inside that scope. Recheck after
  remote work. Add configured login/logout controls and honest missing-config UI.
- [x] Call identity synchronization before any app input/results widgets. Keep
  existing tests explicitly in local mode so they remain deterministic.
- [x] Run UI/history tests followed by the complete suite.

## Task 3 — Setup and verification

- [x] Enable Streamlit's auth extra and install/check required packages. Add a
  blank example config without editing the real ignored secrets file.
- [x] Update AGENTS/PLAN/README/HISTORY/STATUS and dependency attribution. Record
  exact test output and limitations; no live services needed for isolation tests.
- [x] Review authorization boundaries; run compileall, pip check, diff check and
  the complete suite. Report actual OAuth login as unverified until configured.

## Execution ledger

Ruling: implement natively in the existing authorized workspace, preserving the
prior uncommitted project; Git metadata is read-only, so no worktree/commit action.
Native OIDC is the stated default based on the owner's persistence/isolation
request and Streamlit docs; provider registration/credentials remain external.

Task 1 complete: scoped storage, malformed/expired claim denial, legacy isolation.
Task 2 complete: all actions scoped, true fragment cleanup, browser-local exports;
review findings reproduced RED, then fixed GREEN. Task 3 complete: official auth
extra installed, attribution/setup/status updated. Full suite 173 tests plus 142
subtests passed. Real OAuth and browser download remain unverified.
