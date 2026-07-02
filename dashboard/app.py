"""pitchflow — live match analytics dashboard."""
import time
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from deltalake import DeltaTable
from theme import apply_theme

GOLD_DIR    = Path("data/delta/gold")
SILVER_PATH = Path("data/delta/silver/events")
REFRESH_SECONDS = 3

GOLD_SHOTS    = str(GOLD_DIR / "shots")
GOLD_XG       = str(GOLD_DIR / "xg_timeline")
GOLD_STATE    = str(GOLD_DIR / "match_state")
GOLD_MOMENTUM = str(GOLD_DIR / "momentum")

st.set_page_config(page_title="pitchflow", page_icon="\u26bd", layout="wide")
apply_theme()


def load(path):
    """Load a Delta table into pandas — returns empty DataFrame on failure."""
    try:
        return DeltaTable(path).to_pandas()
    except Exception:
        return pd.DataFrame()


def pitch_figure(title=""):
    fig = go.Figure()
    fig.update_layout(
        title=title,
        xaxis=dict(range=[-2, 122], showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(range=[-2, 82], showgrid=False, zeroline=False,
                   showticklabels=False, scaleanchor="x"),
        paper_bgcolor="#1a6b2a",
        plot_bgcolor="#1a6b2a",
        margin=dict(l=0, r=0, t=30, b=0),
        height=400,
        showlegend=True,
    )
    W = dict(color="white", width=2)

    def line(x0, y0, x1, y1):
        fig.add_shape(type="line", x0=x0, y0=y0, x1=x1, y1=y1, line=W)

    def rect(x0, y0, x1, y1):
        fig.add_shape(type="rect", x0=x0, y0=y0, x1=x1, y1=y1, line=W)

    rect(0, 0, 120, 80)
    line(60, 0, 60, 80)
    fig.add_shape(type="circle", x0=54, y0=34, x1=66, y1=46, line=W)
    rect(0, 18, 18, 62)
    rect(0, 30, 6, 50)
    rect(102, 18, 120, 62)
    rect(114, 30, 120, 50)

    G = dict(color="yellow", width=3)
    fig.add_shape(type="rect", x0=-2, y0=36, x1=0, y1=44, line=G)
    fig.add_shape(type="rect", x0=120, y0=36, x1=122, y1=44, line=G)
    return fig


def render_kpi(state, momentum):
    if state.empty:
        st.info("Waiting for data. Run: make up && make bronze && make silver "
                "&& make gold (in 3 terminals) then make replay")
        return

    teams = state["team_name"].tolist()
    t1, t2 = (teams[0], teams[1]) if len(teams) > 1 else (teams[0], "?")

    def val(team, col, default=0):
        r = state[state["team_name"] == team]
        return r[col].iloc[0] if not r.empty and col in r else default

    g1, g2 = int(val(t1, "goals")), int(val(t2, "goals"))
    x1 = round(float(val(t1, "xg_total")), 2)
    x2 = round(float(val(t2, "xg_total")), 2)
    p1 = round(float(val(t1, "win_probability", 0.5)) * 100, 1)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(f"\u26bd {t1}", g1)
        st.caption(f"xG {x1}")
    with c2:
        st.metric(f"\u26bd {t2}", g2)
        st.caption(f"xG {x2}")
    with c3:
        st.markdown("**Win probability**")
        st.progress(p1 / 100, text=f"{t1} {p1}% \u2014 {t2} {round(100 - p1, 1)}%")
        if not momentum.empty:
            st.markdown("**Momentum (last 5 min)**")
            d1 = momentum[momentum["team_name"] == t1]["dominance_pct"]
            dom = float(d1.iloc[0]) if not d1.empty else 0.5
            st.progress(dom, text=f"{t1} {int(dom*100)}% \u2014 {t2} {int((1-dom)*100)}%")


def render_xg_race(xg):
    if xg.empty:
        st.caption("xG data not yet available.")
        return
    teams = sorted(xg["team_name"].unique())
    fig = go.Figure()
    for team in teams:
        t = xg[xg["team_name"] == team].sort_values("minute")
        t = t.assign(xg_cumulative=t["xg_total"].cumsum())
        fig.add_trace(go.Scatter(
            x=t["minute"], y=t["xg_cumulative"],
            mode="lines", name=team,
            line=dict(width=3),
        ))
    fig.update_layout(
        xaxis_title="Minute", yaxis_title="Cumulative xG",
        height=300, margin=dict(l=0, r=0, t=30, b=0),
    )
    st.plotly_chart(fig, use_container_width=True)


def render_shot_map(shots):
    fig = pitch_figure("Shot Map")
    if not shots.empty:
        outcome_colour = {
            "Goal": "gold", "Saved": "dodgerblue", "Off T": "tomato",
            "Blocked": "orange", "Wayward": "grey", "Post": "orchid",
        }
        for team in sorted(shots["team_name"].unique()):
            t = shots[shots["team_name"] == team]
            for outcome, oc in outcome_colour.items():
                o = t[t["shot_outcome"] == outcome]
                if o.empty:
                    continue
                fig.add_trace(go.Scatter(
                    x=o["loc_x"], y=o["loc_y"], mode="markers",
                    name=f"{team} \u2014 {outcome}",
                    marker=dict(
                        size=o["xg"] * 60 + 6,
                        color=oc, opacity=0.8,
                        line=dict(color="white", width=1),
                    ),
                    hovertemplate="<b>%{text}</b><br>xG: %{customdata:.3f}<extra></extra>",
                    text=o["player_name"],
                    customdata=o["xg"],
                ))
    st.plotly_chart(fig, use_container_width=True)


def render_event_log():
    silver = load(str(SILVER_PATH))
    if silver.empty:
        return
    cols = [c for c in ["minute", "second", "team_name", "player_name",
                        "event_type", "xg"] if c in silver.columns]
    st.dataframe(
        silver.sort_values("match_second", ascending=False).head(20)[cols],
        hide_index=True, use_container_width=True,
    )


st.title("\u26bd pitchflow \u2014 Live Match Analytics")
st.caption("Argentina vs France \u00b7 2022 World Cup Final \u00b7 StatsBomb open data")

placeholder = st.empty()

while True:
    state = load(GOLD_STATE)
    xg = load(GOLD_XG)
    shots = load(GOLD_SHOTS)
    momentum = load(GOLD_MOMENTUM)

    with placeholder.container():
        render_kpi(state, momentum)
        st.divider()

        left, right = st.columns(2)
        with left:
            st.subheader("xG Race")
            render_xg_race(xg)
        with right:
            st.subheader("Shot Map")
            render_shot_map(shots)

        st.divider()
        st.subheader("Live Event Log (last 20)")
        render_event_log()

        try:
            version = DeltaTable(str(SILVER_PATH)).version()
        except Exception:
            version = "\u2014"

        st.caption(f"Refreshes every {REFRESH_SECONDS}s \u00b7 "
                   f"Shots: {len(shots)} \u00b7 Silver v{version}")

    time.sleep(REFRESH_SECONDS)
