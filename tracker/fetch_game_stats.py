import logging
import sys
from datetime import datetime, timezone
import requests

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

logger = logging.getLogger(__name__)

# Cache boxscores in memory to avoid redundant network requests in single run
_BOXSCORE_CACHE = {}

def fetch_game_boxscore(game_id):
    if game_id in _BOXSCORE_CACHE:
        return _BOXSCORE_CACHE[game_id]

    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/summary?event={game_id}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        _BOXSCORE_CACHE[game_id] = data
        return data
    except Exception as e:
        logger.warning(f"Failed to fetch boxscore for game {game_id}: {e}")
        return {}

def extract_player_stats_from_boxscore(boxscore_data, player_id=None, player_name=None):
    """
    Extracts stats for a specific athlete from ESPN summary boxscore data.
    """
    if not boxscore_data:
        return None

    # Get game scores
    header = boxscore_data.get("header", {})
    competitions = header.get("competitions", [{}])
    comp = competitions[0] if competitions else {}
    competitors = comp.get("competitors", [])

    final_scores = {}
    for c in competitors:
        team_abbrev = c.get("team", {}).get("abbreviation")
        score = c.get("score")
        if team_abbrev and score is not None:
            final_scores[team_abbrev] = score

    boxscore = boxscore_data.get("boxscore", {})
    players_data = boxscore.get("players", [])

    target_athlete = None
    target_labels = []

    last_name = player_name.split()[-1].lower() if player_name else ""

    for team_box in players_data:
        for stat_cat in team_box.get("statistics", []):
            labels = stat_cat.get("labels", [])
            for ath in stat_cat.get("athletes", []):
                a_info = ath.get("athlete", {})
                a_id = str(a_info.get("id", ""))
                a_display = a_info.get("displayName", "").lower()

                if (player_id and str(player_id) == a_id) or (last_name and last_name in a_display):
                    target_athlete = ath
                    target_labels = labels
                    break
            if target_athlete:
                break
        if target_athlete:
            break

    if not target_athlete:
        return None

    # Check DNP
    if target_athlete.get("didNotPlay"):
        return {
            "has_played": False,
            "dnp_reason": target_athlete.get("reason", "לא שותף / DNP"),
            "final_scores": final_scores
        }

    raw_stats = target_athlete.get("stats", [])
    stats_dict = {}
    for i, label in enumerate(target_labels):
        if i < len(raw_stats):
            stats_dict[label] = raw_stats[i]

    return {
        "has_played": True,
        "minutes": stats_dict.get("MIN", "0"),
        "points": stats_dict.get("PTS", "0"),
        "rebounds": stats_dict.get("REB", "0"),
        "assists": stats_dict.get("AST", "0"),
        "steals": stats_dict.get("STL", "0"),
        "blocks": stats_dict.get("BLK", "0"),
        "fg": stats_dict.get("FG", "0-0"),
        "three_pt": stats_dict.get("3PT", "0-0"),
        "ft": stats_dict.get("FT", "0-0"),
        "turnovers": stats_dict.get("TO", "0"),
        "plus_minus": stats_dict.get("+/-", "0"),
        "final_scores": final_scores
    }

def get_game_player_stats(game, player):
    """
    Calculates 48h spoiler logic and returns full stats payload for a game and player.
    """
    if not game.get("is_completed"):
        return {
            "available": False,
            "is_completed": False
        }

    game_id = game.get("id")
    boxscore = fetch_game_boxscore(game_id)
    player_stats = extract_player_stats_from_boxscore(boxscore, player_id=player.get("espn_id"), player_name=player.get("name"))

    if not player_stats:
        return {
            "available": False,
            "is_completed": True
        }

    # Calculate hours since game
    utc_str = game.get("utc_date", "")
    is_spoiler_period = False
    hours_ago = 999.0

    if utc_str:
        try:
            game_dt = datetime.fromisoformat(utc_str.replace("Z", "+00:00"))
            now_dt = datetime.now(timezone.utc)
            hours_ago = (now_dt - game_dt).total_seconds() / 3600.0
            if 0 <= hours_ago < 48.0:
                is_spoiler_period = True
        except Exception:
            pass

    return {
        "available": True,
        "is_completed": True,
        "hours_ago": round(hours_ago, 1),
        "is_spoiler_period": is_spoiler_period, # True if within 48h (hidden by default)
        "stats": player_stats
    }

if __name__ == "__main__":
    import json
    sample_game = {"id": "401914129", "is_completed": True, "utc_date": "2026-10-08T02:00Z"}
    sample_player = {"espn_id": "4683021", "name": "Deni Avdija"}
    res = get_game_player_stats(sample_game, sample_player)
    print(json.dumps(res, indent=2, ensure_ascii=False))
