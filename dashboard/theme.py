"""Dark-broadcast visual theme for the pitchflow dashboard.

Centralises CSS, palette, and Plotly template in one place. Every chart
and component imports colours/helpers from here, so the look stays
consistent and is changed in a single file.

Aesthetic: black background, lime-green accent, cyan secondary, monospace
for telemetry numbers. Inspired by live sports broadcasts.
"""
from __future__ import annotations

import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st

# Palette
BG_DEEP    = "#000000"
BG_PANEL   = "#0a0f0a"
BG_RAISED  = "#111711"
BORDER     = "#1f2937"
TEXT_HI    = "#f8fafc"
TEXT_MID   = "#cbd5e1"
TEXT_LO    = "#64748b"

LIME       = "#39FF14"   # accent — home team, live indicator
CYAN       = "#22d3ee"   # secondary — away team
AMBER      = "#fbbf24"   # highlights (goals, warnings)
RED        = "#ef4444"   # negative deltas

PITCH_GREEN = "#0d3d1f"
PITCH_LINE  = "#2a5d3c"

TEAM_COLOURS = [LIME, CYAN]


CUSTOM_CSS = f"""
<style>
    @import url(\'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap\');

    .stApp {{
        background-color: {BG_DEEP};
        color: {TEXT_HI};
        font-family: \'Inter\', -apple-system, sans-serif;
    }}

    #MainMenu, footer, header {{ visibility: hidden; }}
    .stDeployButton {{ display: none; }}

    .main .block-container {{
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1400px;
    }}

    .stTabs [data-baseweb="tab-list"] {{
        gap: 4px;
        background-color: {BG_PANEL};
        padding: 4px;
        border-radius: 10px;
        border: 1px solid {BORDER};
    }}
    .stTabs [data-baseweb="tab"] {{
        height: 44px;
        background-color: transparent;
        border-radius: 6px;
        color: {TEXT_MID};
        font-weight: 600;
        font-size: 14px;
        padding: 0 18px;
        border: none;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {LIME};
        color: {BG_DEEP} !important;
    }}

    [data-testid="stMetricValue"] {{
        font-family: \'JetBrains Mono\', monospace;
        font-size: 2.5rem;
        font-weight: 700;
        color: {LIME};
    }}
    [data-testid="stMetricLabel"] {{
        color: {TEXT_LO};
        font-size: 0.7rem;
        text-transform: uppercase;
        letter-spacing: 0.1em;
    }}

    .pf-card {{
        background-color: {BG_PANEL};
        border: 1px solid {BORDER};
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 16px;
    }}

    .pf-badge {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        font-size: 0.7rem;
        font-weight: 700;
        letter-spacing: 0.15em;
        border-radius: 4px;
        font-family: \'JetBrains Mono\', monospace;
    }}
    .pf-badge-live {{
        background-color: {LIME};
        color: {BG_DEEP};
    }}
    .pf-badge-live::before {{
        content: \'●\';
        animation: pulse 1.5s infinite;
    }}
    .pf-badge-replay {{
        background-color: {AMBER};
        color: {BG_DEEP};
    }}
    @keyframes pulse {{
        0%, 100% {{ opacity: 1; }}
        50% {{ opacity: 0.3; }}
    }}

    h1, h2, h3 {{ color: {TEXT_HI}; font-weight: 700; }}
    h3 {{ font-size: 1.1rem; letter-spacing: -0.01em; }}
</style>
"""


def apply_theme() -> None:
    """Inject CSS + register Plotly template. Call once at the top of app.py."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    pio.templates["pitchflow"] = go.layout.Template(
        layout=go.Layout(
            paper_bgcolor=BG_PANEL,
            plot_bgcolor=BG_PANEL,
            font=dict(family="Inter, sans-serif", color=TEXT_HI, size=12),
            colorway=[LIME, CYAN, AMBER, "#a78bfa", "#f472b6"],
            xaxis=dict(
                gridcolor=BORDER, zerolinecolor=BORDER,
                tickfont=dict(color=TEXT_LO),
                title_font=dict(color=TEXT_MID),
            ),
            yaxis=dict(
                gridcolor=BORDER, zerolinecolor=BORDER,
                tickfont=dict(color=TEXT_LO),
                title_font=dict(color=TEXT_MID),
            ),
            legend=dict(
                bgcolor="rgba(0,0,0,0)",
                font=dict(color=TEXT_MID, size=11),
            ),
            margin=dict(l=10, r=10, t=40, b=10),
            hoverlabel=dict(
                bgcolor=BG_RAISED,
                bordercolor=LIME,
                font=dict(family="JetBrains Mono", color=TEXT_HI),
            ),
        )
    )
    pio.templates.default = "pitchflow"
