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

/* The hero's isolated art layer cannot intercept input or cover its content. */
.st-key-relink_hero {
    position: relative;
    isolation: isolate;
    overflow: hidden;
    padding: 2.25rem 31% 2.25rem 2.4rem;
    border: 1px solid var(--rl-line);
    border-radius: 24px;
    background:
        radial-gradient(ellipse at 95% 45%, rgba(214, 152, 84, .13), transparent 68%),
        linear-gradient(125deg, var(--rl-surface), var(--background-color, #080f20));
    box-shadow: 0 16px 50px rgba(0, 0, 0, .16);
    gap: .4rem;
    margin-bottom: .35rem;
}
.st-key-relink_hero > * { position: relative; z-index: 1; }
.st-key-relink_hero::before {
    content: "";
    position: absolute;
    z-index: 0;
    pointer-events: none;
    width: 16rem;
    height: 16rem;
    right: 3.5%;
    top: 50%;
    transform: translateY(-47%);
    border-radius: 50%;
    background:
        radial-gradient(circle at 28% 28%, rgba(255, 225, 176, .45), transparent 48%),
        radial-gradient(circle at 70% 70%, #10192c 8%, #4d3c34 46%, #bd8959 75%, #f6c990 99%);
    box-shadow: -12px -8px 38px rgba(255, 193, 122, .13),
                14px 16px 60px rgba(0, 0, 0, .35),
                inset 2px 2px 3px rgba(255, 228, 188, .4);
    opacity: .8;
}
.st-key-relink_hero::after {
    content: "";
    position: absolute;
    z-index: 0;
    pointer-events: none;
    right: -6%;
    top: 50%;
    width: 31rem;
    height: 12rem;
    border: 1px solid rgba(255, 211, 157, .21);
    border-radius: 50%;
    transform: translateY(-42%) rotate(-28deg);
    box-shadow: 0 0 0 22px rgba(137, 220, 231, .025),
                0 0 0 23px rgba(137, 220, 231, .07);
}
.st-key-relink_hero h1 {
    font-size: clamp(3rem, 5.4vw, 4.8rem) !important;
    line-height: 1.03;
    padding: .2rem 0 .6rem;
}
.st-key-relink_hero h3 {
    font-size: clamp(1.2rem, 2.2vw, 1.7rem);
    line-height: 1.4;
    padding-top: 0;
}
.st-key-relink_hero [data-testid="stCaptionContainer"]:first-child {
    letter-spacing: .1em;
}

.st-key-dataset_input_panel,
.st-key-evidence_panel,
[class*="st-key-dataset_search_card_"] {
    border: 1px solid var(--rl-line);
    border-radius: 18px;
    background: var(--rl-surface);
    box-shadow: 0 10px 32px rgba(0, 0, 0, .12);
    padding: 1.5rem;
}
.st-key-dataset_input_panel { border-top: 2px solid rgba(255, 193, 122, .65); }
.st-key-evidence_panel { border-top: 2px solid rgba(137, 220, 231, .65); }
.st-key-evidence_panel h3 { font-size: 1.3rem; }
[class*="st-key-dataset_search_card_"] { margin-top: .35rem; }
[data-testid="stVerticalBlockBorderWrapper"] > div { border-radius: 16px; }
[data-testid="stSidebar"] { border-right: 1px solid var(--rl-line); }

[data-baseweb="tab-list"] {
    gap: 1.6rem;
    border-bottom: 1px solid var(--rl-line);
}
[data-baseweb="tab"] { padding: .8rem .2rem; font-weight: 600; }
[data-baseweb="tab"][aria-selected="true"] { color: var(--rl-amber); }
[data-testid="stMetricValue"] { font-size: 1.65rem; }
[data-testid="stFileUploader"] { border-radius: 12px; }
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

@media (max-width: 850px) {
    .st-key-relink_hero { padding: 1.8rem 24% 1.8rem 1.8rem; }
    .st-key-relink_hero::before { right: -5rem; width: 14rem; height: 14rem; opacity: .5; }
    .st-key-relink_hero::after { right: -15rem; opacity: .5; }
}
@media (max-width: 640px) {
    .block-container { padding: 4rem 1rem 3rem; }
    .st-key-relink_hero { padding: 1.5rem; border-radius: 18px; }
    .st-key-relink_hero::before, .st-key-relink_hero::after { display: none; }
    .st-key-dataset_input_panel,
    .st-key-evidence_panel,
    [class*="st-key-dataset_search_card_"] { padding: 1.1rem; }
    [data-baseweb="tab-list"] { gap: 1rem; }
}
@media (prefers-reduced-motion: reduce) {
    .stButton button, .stDownloadButton button, .stLinkButton a { transition: none; }
    .stButton button:not(:disabled):hover,
    .stDownloadButton button:not(:disabled):hover,
    .stLinkButton a:hover { transform: none; }
}
</style>
'''
