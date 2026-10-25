# Navigation overlap regression — 2026-10-25

The owner's screenshot was reproduced in local Firefox against Streamlit 1.66.1.
`before.json` records the failed bounding-box assertion: the absolutely positioned
brand intersected the first tab. No elements matched the obsolete BaseWeb tab-list
selector. The installed frontend instead exposes `role="tablist"` and `role="tab"`.

The fix keeps the brand in normal document flow above the native tab strip and
styles the actual ARIA controls. It preserves the three eager native tabs.

`measurements.json` and the six PNGs record the corrected local layout. All six
viewport widths pass non-overlap and page-overflow assertions. The desktop and
390px/320px screenshots were visually inspected. Tab activation and a fallback
with application CSS removed also pass. These are real local browser observations,
not mocked screenshots or evidence about the hosted deployment. No recovery
search or model request was submitted.

To repeat, use three terminals from the project root:

```bash
.venv/bin/python -m streamlit run app.py --server.address 127.0.0.1 --server.port 8510 --server.headless true
```

```bash
mkdir -p /tmp/relink-nav-firefox
firefox --headless --no-remote --profile /tmp/relink-nav-firefox --remote-debugging-port 9231 about:blank
```

```bash
.venv/bin/python scripts/check_navigation_layout.py
```

The optional diagnostic uses the locally installed `websockets` Python package
and Firefox WebDriver BiDi. It is separate from offline pytest and adds no app
dependency. Restart Streamlit before checking imported theme changes. Stop both
local servers afterward; keep the debug port local and use an isolated profile.

Observed automated output (complete pytest and focused UI, respectively):

```text
273 passed, 192 subtests passed in 15.85s
25 passed, 6 subtests passed in 6.40s
```

Compilation and `git diff --check` also pass. No provider live checks were needed
for this presentation-only fix.
