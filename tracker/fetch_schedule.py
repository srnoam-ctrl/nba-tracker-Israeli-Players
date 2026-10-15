import logging
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
import requests

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

logger = logging.getLogger(__name__)

HEBREW_DAYS = {
    0: "יום שני",
    1: "יום שלישי",
    2: "יום רביעי",
    3: "יום חמישי",
    4: "יום שישי",
    5: "יום שבת",
    6: "יום ראשון"
}

def fetch_team_schedule(team_slug="por", target_tz="Asia/Jerusalem"):
    """
    Fetches the team NBA schedule from ESPN public API.
    Fetches Preseason (seasontype=1) and Regular Season (seasontype=2) (and Postseason if present)
    to get the complete season schedule through April.
    Converts all game dates and times to local Israel Time (IST/IDT).
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    raw_events = []
    seen_ids = set()

    # ESPN season types: 1 = Preseason, 2 = Regular Season, 3 = Postseason
    for st in [1, 2, 3]:
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team_slug}/schedule?seasontype={st}"
        try:
            resp = requests.get(url, headers=headers, timeout=12)
            resp.raise_for_status()
            data = resp.json()
            events = data.get("events", [])
            for ev in events:
                eid = str(ev.get("id"))
                if eid and eid not in seen_ids:
                    seen_ids.add(eid)
                    raw_events.append((ev, st))
        except Exception as e:
            logger.warning(f"Failed to fetch NBA schedule for {team_slug} (seasontype={st}): {e}")

    # Fallback to default schedule URL if query params returned nothing
    if not raw_events:
        url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team_slug}/schedule"
        try:
            resp = requests.get(url, headers=headers, timeout=12)
            resp.raise_for_status()
            data = resp.json()
            for ev in data.get("events", []):
                eid = str(ev.get("id"))
                if eid and eid not in seen_ids:
                    seen_ids.add(eid)
                    raw_events.append((ev, 2))
        except Exception as e:
            logger.error(f"Failed to fetch NBA schedule from ESPN for {team_slug}: {e}")
            return []

    games = []
    tz = ZoneInfo(target_tz)

    for ev, st_val in raw_events:
        try:
            game_id = ev.get("id")
            name = ev.get("name", "")
            short_name = ev.get("shortName", "")
            raw_date = ev.get("date")

            if not raw_date:
                continue

            # Parse ISO UTC date
            dt_utc = datetime.fromisoformat(raw_date.replace("Z", "+00:00"))
            dt_il = dt_utc.astimezone(tz)

            competitions = ev.get("competitions", [])
            comp = competitions[0] if competitions else {}
            competitors = comp.get("competitors", [])

            home_team = None
            away_team = None
            is_home = False
            opponent = None

            for c in competitors:
                team_info = c.get("team", {})
                abbrev = (team_info.get("abbreviation") or "").upper()
                t_obj = {
                    "id": team_info.get("id"),
                    "name": team_info.get("displayName"),
                    "abbrev": abbrev,
                    "logo": team_info.get("logo") or f"https://a.espncdn.com/i/teamlogos/nba/500/{abbrev.lower()}.png"
                }
                if c.get("homeAway") == "home":
                    home_team = t_obj
                else:
                    away_team = t_obj

                if abbrev.lower() == team_slug.lower():
                    is_home = (c.get("homeAway") == "home")
                else:
                    opponent = t_obj

            status_desc = comp.get("status", {}).get("type", {}).get("description", "Scheduled")
            status_detail = comp.get("status", {}).get("type", {}).get("detail", "")
            is_completed = comp.get("status", {}).get("type", {}).get("completed", False)

            # Determine season type
            season_info = ev.get("seasonType", {})
            st_id = season_info.get("id") or str(st_val)
            if st_id == "1" or st_val == 1:
                season_type_he = "קדם עונה (Preseason)"
                season_type_en = "Preseason"
            elif st_id == "3" or st_val == 3:
                season_type_he = "פלייאוף (Playoffs)"
                season_type_en = "Postseason"
            else:
                season_type_he = "עונה סדירה (Regular Season)"
                season_type_en = "Regular Season"

            broadcasts = []
            for b in comp.get("broadcasts", []):
                for media in b.get("names", []):
                    if media:
                        broadcasts.append(media)
                short_b = b.get("media", {}).get("shortName")
                if short_b and short_b not in broadcasts:
                    broadcasts.append(short_b)

            game = {
                "id": str(game_id),
                "name": name,
                "short_name": short_name,
                "utc_date": raw_date,
                "date_il": dt_il.strftime("%Y-%m-%d"),
                "time_il": dt_il.strftime("%H:%M"),
                "display_datetime_il": dt_il.strftime("%d/%m/%Y %H:%M"),
                "day_name_en": dt_il.strftime("%A"),
                "day_name_he": HEBREW_DAYS.get(dt_il.weekday(), ""),
                "is_home": is_home,
                "opponent": opponent or {"name": "Opponent", "abbrev": "OPP", "logo": ""},
                "home_team": home_team or {},
                "away_team": away_team or {},
                "status": status_desc,
                "status_detail": status_detail,
                "is_completed": is_completed,
                "season_type": season_type_he,
                "season_type_en": season_type_en,
                "season_type_id": int(st_val) if str(st_val).isdigit() else 2,
                "us_broadcast": ", ".join(broadcasts) if broadcasts else "NBA League Pass"
            }
            games.append(game)
        except Exception as e:
            logger.warning(f"Error parsing event {ev.get('id')}: {e}")
            continue

    games.sort(key=lambda x: x.get("utc_date", ""))
    return games

fetch_portland_schedule = fetch_team_schedule

if __name__ == "__main__":
    import json
    results = fetch_team_schedule("bkn")
    print(f"Fetched {len(results)} games for Brooklyn Nets.")
    if results:
        print("Upcoming sample game:")
        print(json.dumps(results[0], indent=2, ensure_ascii=False))
