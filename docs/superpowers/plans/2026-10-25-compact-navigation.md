# Compact workspace navigation

Owner requests structural changes from the supplied screenshot: ReLink in the
top bar, datasets/papers/license-source navigation, more useful interaction.
Explicit implementation authorization; no engine or provider changes.

Design: replace the large hero and above-fold legal block with a compact native
heading beside a three-tab navigation strip. Preserve native eager tab contents
so forms/results and privacy scope remain intact. Put license/warranty/source
links in the third tab. Paper search becomes a focused input card plus concise
workflow guide. Dataset/paper example buttons populate public inputs through
callbacks, never start remote work or pretend to return results. Keyboard/focus,
responsive/mobile navigation and reduced-motion behavior remain supported.

- [x] Failing AppTests: three tabs/source placement, no hero, examples fill only,
  inputs persist and explicit Find remains required.
- [x] Implement compact shell, native example callbacks and paper panel layout.
- [x] Update scoped CSS for brand/navigation/cards; no remote HTML/assets.
- [x] Run relevant/full suite, review and docs/status; commit/push under standing
  authorization. Browser tooling unavailable unless discovery changes.

Verification:273 tests/192 subtests pass; focused UI40/6. Compileall/whitespace
checks pass. Independent read-only review found no critical/important findings,
with four navigation tests independently passing. Native tabs preserve inputs;
example clicks make no remote calls. No engine changes/live provider requests.
Actual updated browser appearance remains unverified (no executor exposed).
Published feature commit:4f71403; GitHub main push confirmed.
