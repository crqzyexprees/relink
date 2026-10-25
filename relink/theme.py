"""Application-owned presentation assets, with no Streamlit import or side effects.

Render STYLE once with ``st.markdown(STYLE, unsafe_allow_html=True)``. Only this
static CSS is HTML; provider/model/user text must use native Streamlit rendering.
The artwork is original CSS and makes no external font or image requests.
"""

STYLE = '''
<style>
.stApp {
    --rl-amber: #ffc17a;
    --rl-cyan: #89dce7;
    --rl-line: rgba(145, 169, 202, .23);
    --rl-surface: var(--secondary-background-color, #121e32);
    font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
    background-color: var(--background-color, #080f20);
    /* Each star field repeats independently; broad light fades have no edges. */
    background-image:
        radial-gradient(circle at 17px 34px, rgba(226, 237, 255, .35) .7px, transparent 1.2px),
        radial-gradient(circle at 83px 117px, rgba(137, 220, 231, .22) .6px, transparent 1.1px),
        radial-gradient(circle at 141px 63px, rgba(255, 214, 166, .22) .7px, transparent 1.2px),
        radial-gradient(ellipse at 92% 0%, rgba(199, 135, 72, .12), transparent 62%),
        radial-gradient(ellipse at 5% 46%, rgba(44, 103, 145, .13), transparent 68%);
    background-size: 257px 281px, 373px 397px, 461px 443px, 100% 100%, 100% 100%;
    background-attachment: fixed;
}
[data-testid="stHeader"] {
    background: var(--background-color, #080f20);
    border-bottom: 1px solid var(--rl-line);
}
.block-container {
    max-width: 1360px;
    padding-top: 4.5rem;
    padding-bottom: 4rem;
}
h1, h2, h3 { text-wrap: balance; }
h1 { letter-spacing: -.055em; font-weight: 750 !important; }
h2, h3 { letter-spacing: -.025em; }
[data-testid="stCaptionContainer"] { line-height: 1.65; }
[data-testid="stText"] {
    font-family: inherit;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    line-height: 1.65;
}
a { text-underline-offset: .22em; }

.st-key-relink_navigation { gap: 0; }
/* Keep the brand in normal flow. Missing/changed tab styles must never let
   the heading cover native controls. Streamlit 1.66 uses ARIA tabs, not BaseWeb. */
.st-key-relink_brand {
    padding: .65rem .2rem .85rem;
    gap: .85rem;
}
.st-key-relink_brand h1 {
    position: relative;
    font-size: 1.6rem !important;
    line-height: 1.2;
    padding: 0 0 .1rem 2rem;
    margin: 0;
    letter-spacing: -.04em;
}
.st-key-relink_brand h1::before {
    content: "";
    position: absolute;
    left: 0;
    top: .17rem;
    width: 1.25rem;
    height: 1.25rem;
    border-radius: 50%;
    background: radial-gradient(circle at 28% 25%, #ffe8c6, #d89a57 55%, #27334c 90%);
    box-shadow: 0 0 18px rgba(255, 193, 122, .18);
}
.st-key-relink_brand [data-testid="stCaptionContainer"] {
    font-size: .8rem;
    letter-spacing: .03em;
}
.st-key-relink_navigation [role="tablist"] {
    min-height: 3.5rem;
    padding: .3rem;
    align-items: center;
    gap: .55rem;
    border: 1px solid var(--rl-line);
    border-radius: 15px;
    background: rgba(15, 26, 44, .92);
    box-shadow: 0 8px 30px rgba(0, 0, 0, .12);
}
.st-key-relink_navigation [role="tab"] {
    padding: .7rem 1.05rem;
    border-radius: 9px;
    border: 1px solid transparent;
    transition: background .16s ease, border-color .16s ease;
}
.st-key-relink_navigation [role="tab"][aria-selected="true"] {
    color: var(--rl-amber);
    background: rgba(255, 193, 122, .09);
    border-color: rgba(255, 193, 122, .24);
}
.st-key-relink_navigation [role="tab"]:hover {
    background: rgba(137, 220, 231, .07);
    border-color: rgba(137, 220, 231, .2);
}
.st-key-relink_navigation [role="tabpanel"] { padding-top: .65rem; }

.st-key-dataset_input_panel,
.st-key-evidence_panel,
.st-key-paper_input_panel,
.st-key-paper_guide,
[class*="st-key-dataset_search_card_"] {
    border: 1px solid var(--rl-line);
    border-radius: 18px;
    background: var(--rl-surface);
    box-shadow: 0 10px 32px rgba(0, 0, 0, .12);
    padding: 1.5rem;
}
.st-key-dataset_input_panel { border-top: 2px solid rgba(255, 193, 122, .65); }
.st-key-paper_input_panel { border-top: 2px solid rgba(255, 193, 122, .65); }
.st-key-paper_guide { border-top: 2px solid rgba(137, 220, 231, .65); }
.st-key-paper_guide h3 { font-size: 1.3rem; }
.st-key-evidence_panel { border-top: 2px solid rgba(137, 220, 231, .65); }
.st-key-evidence_panel h3 { font-size: 1.3rem; }
[class*="st-key-dataset_search_card_"] { margin-top: .35rem; }
[data-testid="stVerticalBlockBorderWrapper"] > div { border-radius: 16px; }
[data-testid="stSidebar"] { border-right: 1px solid var(--rl-line); }

[role="tablist"] {
    gap: 1.6rem;
    border-bottom: 1px solid var(--rl-line);
}
[role="tab"] { padding: .8rem .2rem; font-weight: 600; }
[role="tab"][aria-selected="true"] { color: var(--rl-amber); }
[data-testid="stMetricValue"] { font-size: 1.65rem; }
[data-testid="stFileUploader"] { border-radius: 12px; }
[data-testid="stRadio"] [role="radiogroup"] { gap: .45rem; }
[data-testid="stRadio"] [role="radiogroup"] > label {
    padding: .6rem .8rem;
    border: 1px solid var(--rl-line);
    border-radius: 10px;
    background: rgba(8, 15, 32, .35);
    transition: border-color .16s ease, background .16s ease;
}
[data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) {
    border-color: rgba(255, 193, 122, .5);
    background: rgba(255, 193, 122, .07);
}
[class*="st-key-paper_example_"] button,
[class*="st-key-dataset_example_"] button {
    border-radius: 999px;
    font-size: .82rem;
    background: rgba(137, 220, 231, .035);
}
.stButton button, .stDownloadButton button, .stLinkButton a {
    border-radius: 10px;
    min-height: 2.6rem;
    transition: border-color .16s ease, box-shadow .16s ease, transform .16s ease;
}
.stButton button[kind="primary"],
.stFormSubmitButton button[kind="primary"] {
    background: var(--rl-amber);
    border-color: var(--rl-amber);
    color: #141c2a;
    font-weight: 650;
    box-shadow: 0 4px 20px rgba(255, 193, 122, .13);
}
.stButton button[kind="primary"]:disabled,
.stFormSubmitButton button[kind="primary"]:disabled {
    background: var(--rl-surface);
    border-color: var(--rl-line);
    color: var(--text-color, #f2eee7);
    opacity: .5;
    box-shadow: none;
}
@media (hover: hover) {
    .stButton button:not(:disabled):hover,
    .stDownloadButton button:not(:disabled):hover,
    .stLinkButton a:hover {
        border-color: var(--rl-amber);
        box-shadow: 0 4px 20px rgba(255, 193, 122, .16);
        transform: translateY(-1px);
    }
}
.stApp :is(button, a, input, textarea, [role="tab"], [role="radio"]):focus-visible {
    outline: 2px solid var(--rl-cyan);
    outline-offset: 3px;
}

@media (max-width: 640px) {
    .block-container { padding: 4rem 1rem 3rem; }
    .st-key-relink_brand { padding: .2rem 0 .8rem; }
    .st-key-relink_brand [data-testid="stCaptionContainer"] { display: none; }
    .st-key-relink_navigation [role="tablist"] {
        padding: .3rem;
        min-height: 3.5rem;
        overflow-x: auto;
        gap: .15rem;
    }
    .st-key-relink_navigation [role="tab"] { padding: .65rem .6rem; }
    .st-key-dataset_input_panel,
    .st-key-evidence_panel,
    .st-key-paper_input_panel,
    .st-key-paper_guide,
    [class*="st-key-dataset_search_card_"] { padding: 1.1rem; }
    [role="tablist"] { gap: 1rem; }
}
@media (prefers-reduced-motion: reduce) {
    .stButton button, .stDownloadButton button, .stLinkButton a { transition: none; }
    .st-key-relink_navigation [role="tab"],
    [data-testid="stRadio"] [role="radiogroup"] > label { transition: none; }
    .stButton button:not(:disabled):hover,
    .stDownloadButton button:not(:disabled):hover,
    .stLinkButton a:hover { transform: none; }
}
</style>
'''
