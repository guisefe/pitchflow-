"""pitchflow — live match analytics dashboard.

Professional design with hero scoreboard, shot map (mplsoccer), and stats bars.
"""
import sys
import textwrap
import time
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from deltalake import DeltaTable

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.theme import BG_PANEL, CYAN, LIME, TEXT_HI, TEXT_LO, apply_theme  # noqa: E402
from dashboard.viz.shot_map import build_shot_map  # noqa: E402

GOLD_DIR = Path("data/delta/gold")
SILVER_PATH = Path("data/delta/silver/events")

st.set_page_config(page_title="pitchflow", page_icon="\u26bd", layout="wide")
apply_theme()


def render_html(html: str) -> None:
    """Render HTML in Streamlit, stripping Python's indentation first.

    Markdown treats 4+ leading spaces as a code block. Since our HTML
    lives inside indented Python functions, we must dedent it before
    st.markdown() sees it -- otherwise it renders as literal text
    instead of an actual scoreboard.
    """
    st.markdown(textwrap.dedent(html), unsafe_allow_html=True)


@st.cache_data(ttl=3)
def load(path):
    """Load a Delta table into pandas. Cache for 3 seconds."""
    try:
        return DeltaTable(str(path)).to_pandas()
    except Exception:
        return pd.DataFrame()


def render_hero(state: pd.DataFrame) -> None:
    """Large, clear scoreboard at top. Sets visual hierarchy."""
    if state.empty or len(state) != 2:
        st.warning(
            "\u23f3 Waiting for data... Run: make up && make bronze && "
            "make silver && make gold && make replay"
        )
        return

    t1_name, t2_name = state["team_name"].iloc[0], state["team_name"].iloc[1]
    t1 = state[state["team_name"] == t1_name].iloc[0]
    t2 = state[state["team_name"] == t2_name].iloc[0]

    html = f"""
    <div style="background: linear-gradient(90deg, rgba(57,255,20,0.1) 0%, rgba(10,15,10,0.95) 50%, rgba(34,211,238,0.1) 100%); border: 1px solid #3a4a3f; border-radius: 12px; padding: 32px 24px; margin-bottom: 24px;">
        <div style="font-size: 12px; color: #94a3b8; margin-bottom: 12px; letter-spacing: 0.12em; text-transform: uppercase; text-align: center;">
            2022 FIFA World Cup Final &middot; REPLAY MODE
        </div>
        <div style="display: grid; grid-template-columns: 1fr 120px 1fr; gap: 24px; align-items: center; text-align: center;">
            <div>
                <div style="font-size: 56px; font-weight: 700; color: #39FF14; font-family: 'JetBrains Mono', monospace; line-height: 1;">{int(t1['goals'])}</div>
                <div style="font-size: 16px; color: #f8fafc; margin-top: 12px; font-weight: 600;">{t1_name.upper()}</div>
                <div style="font-size: 11px; color: #94a3b8; margin-top: 6px;">xG {float(t1['xg_total']):.2f}</div>
            </div>
            <div>
                <div style="font-size: 20px; color: #cbd5e1; font-weight: 300;">90'+{max(0, int(t1['latest_minute']) - 90)}'</div>
                <div style="font-size: 10px; color: #64748b; margin-top: 8px; text-transform: uppercase;">60&times; Speed</div>
            </div>
            <div>
                <div style="font-size: 56px; font-weight: 700; color: #22d3ee; font-family: 'JetBrains Mono', monospace; line-height: 1;">{int(t2['goals'])}</div>
                <div style="font-size: 16px; color: #f8fafc; margin-top: 12px; font-weight: 600;">{t2_name.upper()}</div>
                <div style="font-size: 11px; color: #94a3b8; margin-top: 6px;">xG {float(t2['xg_total']):.2f}</div>
            </div>
        </div>
    </div>
    """
    render_html(html)


def render_stats_bars(state: pd.DataFrame) -> None:
    """Shot count comparison -- total shots and shots on target."""
    if state.empty or len(state) != 2:
        return

    t1_name = state["team_name"].iloc[0]
    t2_name = state["team_name"].iloc[1]

    shots_all = load(GOLD_DIR / "shots")
    on_target = {"Goal", "Saved"}

    def counts(team):
        t = shots_all[shots_all["team_name"] == team]
        total = len(t)
        target = len(t[t["shot_outcome"].isin(on_target)])
        return total, target

    total1, target1 = counts(t1_name) if not shots_all.empty else (0, 0)
    total2, target2 = counts(t2_name) if not shots_all.empty else (0, 0)

    html = f"""
    <div style="background: {BG_PANEL}; border: 1px solid #3a4a3f; border-radius: 10px; padding: 20px; margin-bottom: 24px;">
        <div style="display: grid; grid-template-columns: 1fr 160px 1fr; gap: 20px; align-items: center; margin-bottom: 14px;">
            <div style="text-align: right;">
                <div style="font-size: 28px; font-weight: 700; color: #39FF14; font-family: 'JetBrains Mono', monospace;">{total1}</div>
                <div style="font-size: 10px; color: #94a3b8; margin-top: 4px; text-transform: uppercase;">Total Shots</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 10px; color: #64748b; text-transform: uppercase; font-weight: 600;">Shots</div>
            </div>
            <div>
                <div style="font-size: 28px; font-weight: 700; color: #22d3ee; font-family: 'JetBrains Mono', monospace;">{total2}</div>
                <div style="font-size: 10px; color: #94a3b8; margin-top: 4px; text-transform: uppercase;">Total Shots</div>
            </div>
        </div>
        <div style="display: grid; grid-template-columns: 1fr 160px 1fr; gap: 20px; align-items: center;">
            <div style="text-align: right;">
                <div style="font-size: 28px; font-weight: 700; color: #39FF14; font-family: 'JetBrains Mono', monospace;">{target1}</div>
                <div style="font-size: 10px; color: #94a3b8; margin-top: 4px; text-transform: uppercase;">On Target</div>
            </div>
            <div style="text-align: center;">
                <div style="font-size: 10px; color: #64748b; text-transform: uppercase; font-weight: 600;">Accuracy</div>
            </div>
            <div>
                <div style="font-size: 28px; font-weight: 700; color: #22d3ee; font-family: 'JetBrains Mono', monospace;">{target2}</div>
                <div style="font-size: 10px; color: #94a3b8; margin-top: 4px; text-transform: uppercase;">On Target</div>
            </div>
        </div>
    </div>
    """
    render_html(html)


# ============================================================================
# MAIN UI
# ============================================================================

st.title("\u26bd pitchflow")
st.caption("Real-time football match analytics \u00b7 2022 World Cup Final")
st.divider()

state = load(GOLD_DIR / "match_state")
shots = load(GOLD_DIR / "shots")
xg = load(GOLD_DIR / "xg_timeline")

render_hero(state)
render_stats_bars(state)

col1, col2 = st.columns(2)

with col1:
    st.subheader("Shot Map")
    if not shots.empty and not state.empty:
        t1_name = state["team_name"].iloc[0]
        t2_name = state["team_name"].iloc[1]
        fig = build_shot_map(shots, t1_name, t2_name)
        st.pyplot(fig, use_container_width=True)
    else:
        st.info("Shots data not available yet.")

with col2:
    st.subheader("xG Race")
    if not xg.empty:
        fig = go.Figure()
        for team, colour in [
            (state["team_name"].iloc[0] if not state.empty else "Team 1", LIME),
            (state["team_name"].iloc[1] if not state.empty else "Team 2", CYAN),
        ]:
            t = xg[xg["team_name"] == team].sort_values("minute")
            if not t.empty:
                t = t.assign(xg_cumulative=t["xg_total"].cumsum())
                fig.add_trace(go.Scatter(
                    x=t["minute"], y=t["xg_cumulative"],
                    mode="lines", name=team,
                    line=dict(color=colour, width=3),
                ))
        fig.update_layout(
            xaxis_title="Minute", yaxis_title="Cumulative xG",
            paper_bgcolor=BG_PANEL, plot_bgcolor=BG_PANEL,
            font=dict(color=TEXT_HI),
            height=400, margin=dict(l=0, r=0, t=30, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("xG data not available yet.")

st.divider()
st.caption(
    "Streaming architecture: Kafka (Redpanda) \u2192 Spark Structured Streaming "
    "\u2192 Delta Lake \u2192 Live Dashboard"
)
