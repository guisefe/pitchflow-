"""Professional shot map built with mplsoccer.

One question answered: where were the chances created, and how big were they?

Design decisions:
- Each team attacks one half (home -> right, away -> left), like broadcast graphics.
- Marker size encodes xG; filled circles are goals, hatched outlines are misses.
- Dark pitch matches the dashboard theme (single source of truth: theme.py).
"""
import matplotlib.pyplot as plt
from mplsoccer import Pitch
from theme import BG_PANEL, CYAN, LIME, TEXT_HI, TEXT_LO

PITCH_LINE_DARK = "#3a4a3f"


def build_shot_map(shots, home_team: str, away_team: str):
    """Return a matplotlib figure with both teams' shots on one pitch.

    shots: DataFrame with columns team_name, player_name, loc_x, loc_y,
           xg, shot_outcome (StatsBomb coordinates: 120 x 80).
    """
    pitch = Pitch(
        pitch_type="statsbomb",
        pitch_color=BG_PANEL,
        line_color=PITCH_LINE_DARK,
        linewidth=1.2,
        line_zorder=2,
        goal_type="box",
    )
    fig, ax = pitch.draw(figsize=(10, 6.5))
    fig.set_facecolor(BG_PANEL)

    if shots.empty:
        ax.text(60, 40, "No shots yet", color=TEXT_LO,
                ha="center", va="center", fontsize=14)
        return fig

    for team, colour, attack_right in [
        (home_team, LIME, True),
        (away_team, CYAN, False),
    ]:
        t = shots[shots["team_name"] == team].copy()
        if t.empty:
            continue

        # Mirror coordinates so this team's shots appear on its attacking half.
        if not attack_right:
            t["loc_x"] = 120 - t["loc_x"]
            t["loc_y"] = 80 - t["loc_y"]

        goals = t[t["shot_outcome"] == "Goal"]
        misses = t[t["shot_outcome"] != "Goal"]

        # Misses: hatched outline only (community-standard style).
        pitch.scatter(
            misses["loc_x"], misses["loc_y"],
            s=misses["xg"] * 900 + 80,
            c="none", hatch="///",
            edgecolors=colour, linewidths=1.2, alpha=0.55,
            ax=ax, zorder=3,
        )
        # Goals: filled, white edge, on top.
        pitch.scatter(
            goals["loc_x"], goals["loc_y"],
            s=goals["xg"] * 900 + 120,
            c=colour, edgecolors="white", linewidths=1.5,
            ax=ax, zorder=4,
        )
        # Annotate goal scorers (last name only, small, non-intrusive).
        for _, row in goals.iterrows():
            surname = str(row["player_name"]).split()[-1]
            pitch.annotate(
                surname, (row["loc_x"], row["loc_y"] - 3.2),
                ax=ax, color=TEXT_HI, fontsize=7.5,
                ha="center", va="top", zorder=5,
            )

    # Team labels on each attacking half.
    ax.text(90, -2.5, home_team.upper(), color=LIME, fontsize=10,
            fontweight="bold", ha="center", va="bottom")
    ax.text(30, -2.5, away_team.upper(), color=CYAN, fontsize=10,
            fontweight="bold", ha="center", va="bottom")

    return fig
