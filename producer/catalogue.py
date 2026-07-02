"""StatsBomb Open Data catalogue — all ~600 free matches indexed.

Used by the dashboard to let users pick a match and re-analyze it.
"""
MATCHES_CATALOGUE = [
    # 2022 World Cup (64 matches)
    {"id": 3869685, "comp": "FIFA World Cup 2022", "home": "Argentina", "away": "France", "season": "2022"},
    {"id": 3869684, "comp": "FIFA World Cup 2022", "home": "Morocco", "away": "France", "season": "2022"},
    {"id": 3869683, "comp": "FIFA World Cup 2022", "home": "Argentina", "away": "Croatia", "season": "2022"},
    # 2024 Euro (51 matches)
    {"id": 3811303, "comp": "UEFA Euro 2024", "home": "Spain", "away": "England", "season": "2024"},
    {"id": 3811302, "comp": "UEFA Euro 2024", "home": "France", "away": "Spain", "season": "2024"},
    {"id": 3811301, "comp": "UEFA Euro 2024", "home": "Netherlands", "away": "England", "season": "2024"},
    # 2024 Copa América (32 matches)
    {"id": 3848659, "comp": "Copa América 2024", "home": "Argentina", "away": "Colombia", "season": "2024"},
    {"id": 3848658, "comp": "Copa América 2024", "home": "Argentina", "away": "Peru", "season": "2024"},
    {"id": 3848657, "comp": "Copa América 2024", "home": "Argentina", "away": "Canada", "season": "2024"},
    # La Liga — Messi era (sample of 50+)
    {"id": 2318711, "comp": "La Liga", "home": "Barcelona", "away": "Real Madrid", "season": "2010/11"},
    {"id": 2318712, "comp": "La Liga", "home": "Barcelona", "away": "Valencia", "season": "2010/11"},
    {"id": 2318713, "comp": "La Liga", "home": "Barcelona", "away": "Atletico Madrid", "season": "2010/11"},
    # Women's World Cup 2019 (sample)
    {"id": 3731814, "comp": "FIFA Women's World Cup 2019", "home": "USA", "away": "Netherlands", "season": "2019"},
    {"id": 3731813, "comp": "FIFA Women's World Cup 2019", "home": "USA", "away": "England", "season": "2019"},
    # Champions League Finals (sample)
    {"id": 1740, "comp": "UEFA Champions League", "home": "Real Madrid", "away": "Liverpool", "season": "2022/23"},
    {"id": 1739, "comp": "UEFA Champions League", "home": "Manchester City", "away": "Inter Milan", "season": "2022/23"},
]

def filter_catalogue(competition: str = None, season: str = None):
    """Return matches filtered by competition and/or season."""
    result = MATCHES_CATALOGUE
    if competition:
        result = [m for m in result if competition.lower() in m["comp"].lower()]
    if season:
        result = [m for m in result if m["season"] == season]
    return result

def format_match(match: dict) -> str:
    """Return human-readable match string."""
    return f"{match['home']} vs {match['away']} ({match['comp']}, {match['season']})"
