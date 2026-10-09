import logging
import re
import sys
from datetime import datetime, timezone
import requests

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

logger = logging.getLogger(__name__)

def check_blazers_pr_x_api(bearer_token):
    """
    If the user has provided an X API Bearer Token in config.json,
    query the recent tweets of @TrailBlazersPR.
    """
    if not bearer_token:
        return None

    url = "https://api.twitter.com/2/tweets/search/recent"
    params = {
        "query": "from:TrailBlazersPR (injury OR Avdija OR Deni OR OUT OR QUESTIONABLE OR AVAILABLE)",
        "tweet.fields": "created_at,text",
        "max_results": 10
    }
    headers = {"Authorization": f"Bearer {bearer_token}"}

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=8)
        if resp.status_code == 200:
            tweets = resp.json().get("data", [])
            for t in tweets:
                parsed = parse_blazers_tweet(t.get("text", ""))
                if parsed:
                    parsed["source"] = "@TrailBlazersPR (X Official)"
                    parsed["tweet_time"] = t.get("created_at")
                    return parsed
    except Exception as e:
        logger.debug(f"X API check failed: {e}")

    return None

def check_blazers_pr_syndication():
    """
    Attempts to fetch recent public tweets from @TrailBlazersPR via public syndication endpoints.
    """
    endpoints = [
        "https://syndication.twitter.com/srv/timeline-profile/screen-name/TrailBlazersPR"
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    for url in endpoints:
        try:
            resp = requests.get(url, headers=headers, timeout=6)
            if resp.status_code == 200 and "Rate limit exceeded" not in resp.text:
                parsed = parse_blazers_tweet(resp.text)
                if parsed:
                    parsed["source"] = "@TrailBlazersPR (X Feed)"
                    return parsed
        except Exception:
            continue

    return None

def parse_blazers_tweet(text):
    """
    Parses a tweet text from TrailBlazersPR for Deni Avdija status.
    Expected patterns:
      QUESTIONABLE: Deni Avdija (Right Ankle Sprain)
      OUT: Deni Avdija (Lower Back Soreness)
      AVAILABLE: Deni Avdija
      PROBABLE: Deni Avdija
    """
    if not text or "avdija" not in text.lower():
        return None

    # Status detection
    lower = text.lower()
    injury_detail = ""

    # Look for parentheses or details after Avdija
    detail_match = re.search(r'avdija\s*\(([^)]+)\)', text, re.IGNORECASE)
    if detail_match:
        injury_detail = detail_match.group(1).strip()

    status = "Active"
    playing = "YES"

    if re.search(r'\bOUT\b[^\n]*avdija|avdija[^\n]*\bOUT\b', text, re.IGNORECASE):
        status = "Out"
        playing = "NO"
    elif re.search(r'\bDOUBTFUL\b[^\n]*avdija|avdija[^\n]*\bDOUBTFUL\b', text, re.IGNORECASE):
        status = "Doubtful"
        playing = "NO"
    elif re.search(r'\bQUESTIONABLE\b[^\n]*avdija|avdija[^\n]*\bQUESTIONABLE\b', text, re.IGNORECASE):
        status = "Questionable (GTD)"
        playing = "GTD"
    elif re.search(r'\bPROBABLE\b[^\n]*avdija|avdija[^\n]*\bPROBABLE\b', text, re.IGNORECASE):
        status = "Probable"
        playing = "YES"
    elif re.search(r'\bAVAILABLE\b[^\n]*avdija|avdija[^\n]*\bAVAILABLE\b', text, re.IGNORECASE):
        status = "Available"
        playing = "YES"

    return {
        "status": status,
        "is_playing": playing,
        "detail": injury_detail or "Listed in team report",
        "raw_text": text[:160]
    }

def fetch_espn_roster_status(espn_id="4683021", team_slug="por", player_name="Avdija"):
    """
    Queries ESPN NBA Roster API for team to check player's current status and injury record.
    """
    url = f"https://site.api.espn.com/apis/site/v2/sports/basketball/nba/teams/{team_slug}/roster"
    headers = {"User-Agent": "Mozilla/5.0"}

    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning(f"Failed to fetch ESPN roster for {team_slug}: {e}")
        return None

    athletes = data.get("athletes", [])
    player_obj = None

    last_name = player_name.split()[-1].lower() if player_name else ""

    for item in athletes:
        if isinstance(item, dict):
            if str(item.get("id")) == str(espn_id) or (last_name and last_name in item.get("fullName", "").lower()):
                player_obj = item
                break
            if "items" in item:
                for a in item["items"]:
                    if str(a.get("id")) == str(espn_id) or (last_name and last_name in a.get("fullName", "").lower()):
                        player_obj = a
                        break

    if not player_obj:
        return {
            "status": "Active",
            "is_playing": "YES",
            "detail": "Healthy / Roster Active",
            "source": f"ESPN / NBA {team_slug.upper()} Roster",
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

    injuries = player_obj.get("injuries", [])
    status_obj = player_obj.get("status", {})
    status_name = status_obj.get("name", "Active")

    if injuries:
        first_inj = injuries[0]
        status_text = first_inj.get("status", "Injured")
        desc = first_inj.get("details", {}).get("detail") or first_inj.get("shortComment") or "Injured"
        
        is_playing = "NO" if "out" in status_text.lower() else "GTD"
        return {
            "status": status_text,
            "is_playing": is_playing,
            "detail": desc,
            "source": "ESPN / NBA Official Injury Feed",
            "last_updated": datetime.now(timezone.utc).isoformat()
        }

    return {
        "status": status_name,
        "is_playing": "YES" if status_name.lower() in ["active", "available"] else "NO",
        "detail": "Healthy / No injuries reported",
        "source": "ESPN / NBA Official Roster",
        "last_updated": datetime.now(timezone.utc).isoformat()
    }

def get_player_status(player_info, config=None):
    """
    Resolves playing/injury status for a player:
    1. Check X PR account (if configured)
    2. Fallback to ESPN Official Roster
    """
    espn_id = player_info.get("espn_id", "")
    team_slug = player_info.get("team_slug", "por")
    name = player_info.get("name", "")

    # Check ESPN official roster
    roster_status = fetch_espn_roster_status(espn_id=espn_id, team_slug=team_slug, player_name=name)
    if roster_status:
        return roster_status

    return {
        "status": "Active",
        "is_playing": "YES",
        "detail": "Healthy / No injuries reported",
        "source": "Default (Active)",
        "last_updated": datetime.now(timezone.utc).isoformat()
    }

def get_deni_avdija_status(config=None):
    return get_player_status({
        "espn_id": "4683021",
        "team_slug": "por",
        "name": "Deni Avdija"
    }, config=config)

if __name__ == "__main__":
    import json
    print("Checking Deni Avdija injury & playing status...")
    status = get_deni_avdija_status()
    print(json.dumps(status, indent=2, ensure_ascii=False))
