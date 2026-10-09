import logging
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

logger = logging.getLogger(__name__)

# Common NBA team name mappings in Hebrew for Israeli broadcasts
NBA_HEBREW_TEAMS = {
    "GS": ["גולדן סטייט", "ווריורס", "golden state"],
    "LAL": ["לוס אנג'לס לייקרס", "לייקרס", "lakers"],
    "LAC": ["לוס אנג'לס קליפרס", "קליפרס", "clippers"],
    "BOS": ["בוסטון", "סלטיקס", "celtics"],
    "MIL": ["מילווקי", "באקס", "bucks"],
    "DEN": ["דנוור", "נאגטס", "nuggets"],
    "PHX": ["פיניקס", "סאנס", "suns"],
    "MIA": ["מיאמי", "היט", "heat"],
    "NY": ["ניו יורק", "ניקס", "knicks"],
    "PHI": ["פילדלפיה", "סיקסרס", "76ers"],
    "DAL": ["דאלאס", "מאבריקס", "mavericks"],
    "MIN": ["מינסוטה", "טימברוולבס", "timberwolves"],
    "OKC": ["אוקלהומה", "ת'אנדר", "thunder"],
    "SAC": ["סקרמנטו", "קינגס", "kings"],
    "HOU": ["יוסטון", "רוקטס", "rockets"],
    "SAS": ["סן אנטוניו", "ספרס", "spurs"],
    "MEM": ["ממפיס", "גריזליס", "grizzlies"],
    "NOP": ["ניו אורלינס", "פליקנס", "pelicans"],
    "UTA": ["יוטה", "ג'אז", "jazz"],
    "CHI": ["שיקגו", "בולס", "bulls"],
    "CLE": ["קליבלנד", "קאבס", "cavaliers"],
    "IND": ["אינדיאנה", "פייסרס", "pacers"],
    "ORL": ["אורלנדו", "מג'יק", "magic"],
    "ATL": ["אטלנטה", "הוקס", "hawks"],
    "BKN": ["ברוקלין", "נטס", "nets"],
    "TOR": ["טורונטו", "ראפטורס", "raptors"],
    "CHA": ["שארלוט", "הורנטס", "hornets"],
    "WAS": ["וושינגטון", "וויזארדס", "wizards"],
    "DET": ["דטרויט", "פיסטונס", "pistons"],
    "LON": ["לונדון", "לונדון ליונס", "london lions"]
}

TEAM_KEYWORDS = {
    "POR": ["פורטלנד", "בלייזרס", "טרייל בלייזרס", "טריילבלייזרס", "portland", "blazers", "trail blazers", "דני אבדיה", "אבדיה"],
    "BKN": ["ברוקלין", "נטס", "brooklyn", "nets", "בן שרף", "דני וולף", "שרף", "וולף"],
    "SAC": ["סקרמנטו", "קינגס", "sacramento", "kings", "עמנואל שארפ", "שארפ"]
}

def is_time_close(time_str1, time_str2, max_diff_minutes=75):
    """
    Checks if two 'HH:MM' times are within max_diff_minutes of each other.
    """
    try:
        t1 = datetime.strptime(time_str1, "%H:%M")
        t2 = datetime.strptime(time_str2, "%H:%M")
        diff = abs((t1 - t2).total_seconds()) / 60
        # Check wrap around 24 hours if needed
        return diff <= max_diff_minutes or (1440 - diff) <= max_diff_minutes
    except Exception:
        return False

def match_game_to_broadcast(game, broadcast_list, team_slug="por"):
    """
    Attempts to match an NBA game to an Israeli TV broadcast entry.
    """
    game_date_il = game.get("date_il") # YYYY-MM-DD
    game_time_il = game.get("time_il") # HH:MM
    opp_abbrev = game.get("opponent", {}).get("abbrev", "").upper()
    opp_name = game.get("opponent", {}).get("name", "").lower()

    opp_hebrew_keywords = NBA_HEBREW_TEAMS.get(opp_abbrev, [])
    team_keywords = TEAM_KEYWORDS.get(team_slug.upper(), ["nba"])
    
    # Dates to check in TV guide (same day, previous day, next day)
    try:
        g_date = datetime.strptime(game_date_il, "%Y-%m-%d")
        candidate_dates = [
            g_date.strftime("%Y-%m-%d"),
            (g_date - timedelta(days=1)).strftime("%Y-%m-%d"),
            (g_date + timedelta(days=1)).strftime("%Y-%m-%d")
        ]
    except Exception:
        candidate_dates = [game_date_il]

    # Filter broadcasts around the candidate dates
    nearby_broadcasts = [b for b in broadcast_list if b.get("date") in candidate_dates]

    best_match = None
    highest_score = 0

    for b in nearby_broadcasts:
        title_lower = b.get("title", "").lower()
        score = 0

        # Direct mention of the player's team
        for kw in team_keywords:
            if kw.lower() in title_lower:
                score += 10
                break

        # Mention of opponent in Hebrew or English
        for opp_kw in opp_hebrew_keywords:
            if opp_kw.lower() in title_lower:
                score += 5
                break
        if opp_name and opp_name in title_lower:
            score += 5

        # Mention of NBA
        if "nba" in title_lower or "אן.בי.אי" in title_lower or "אן בי איי" in title_lower:
            score += 3

        # Time closeness check
        if is_time_close(game_time_il, b.get("time")):
            score += 5

        # Live broadcast bonus
        if b.get("is_live"):
            score += 2

        if score > highest_score and score >= 10:
            highest_score = score
            best_match = b

    return best_match

def correlate_games_with_tv_and_status(games, broadcasts, player_status, days_ahead_limit=7, team_slug="por"):
    """
    Merges schedule, TV listings, and player status into a unified game object.
    """
    enriched_games = []
    now_il = datetime.now(ZoneInfo("Asia/Jerusalem"))
    limit_date = (now_il + timedelta(days=days_ahead_limit)).strftime("%Y-%m-%d")

    for g in games:
        matched_tv = match_game_to_broadcast(g, broadcasts, team_slug=team_slug)
        game_date = g.get("date_il")

        if matched_tv:
            channel_info = {
                "channel_name": matched_tv.get("channel"),
                "is_live": matched_tv.get("is_live", True),
                "broadcast_title": matched_tv.get("title"),
                "broadcast_time": matched_tv.get("time"),
                "status": "CONFIRMED_BROADCAST",
                "badge": "שידור חי בערוץ הספורט" if matched_tv.get("is_live") else "שידור בערוץ הספורט"
            }
        elif game_date <= limit_date:
            channel_info = {
                "channel_name": "טרם עודכן שידור ישראלי (זמין ב-NBA League Pass)",
                "is_live": False,
                "broadcast_title": "",
                "broadcast_time": "",
                "status": "NOT_SCHEDULED_YET",
                "badge": "League Pass / טרם פורסם"
            }
        else:
            channel_info = {
                "channel_name": f"לוח שידורים טרם נפתח (יעודכן כ-{days_ahead_limit} ימים לפני המשחק)",
                "is_live": False,
                "broadcast_title": "",
                "broadcast_time": "",
                "status": "PENDING_HORIZON",
                "badge": "עתידי"
            }

        # Attach player status
        is_playing = player_status.get("is_playing", "YES")
        status_text = player_status.get("status", "Active")
        detail = player_status.get("detail", "")
        source = player_status.get("source", "Official")

        status_info = {
            "is_playing": is_playing,
            "status": status_text,
            "detail": detail,
            "source": source,
            "badge_icon": "✅" if is_playing == "YES" else ("🟡" if is_playing == "GTD" else "🔴"),
            "badge_text": f"כשיר ומשחק (Available)" if is_playing == "YES" else (f"בספק ({status_text})" if is_playing == "GTD" else f"בחוץ ({status_text})")
        }

        enriched_games.append({
            **g,
            "tv_broadcast": channel_info,
            "player_status": status_info,
            "deni_status": status_info
        })

    return enriched_games
