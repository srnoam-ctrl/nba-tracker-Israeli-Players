import logging
import sys
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import requests

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

logger = logging.getLogger(__name__)

CHANNEL_ID = "UCQDaEuX375Wfhz5Q3JGHu5w"
CHANNEL_URL = "https://www.youtube.com/@PiniBarel"
RSS_URL = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"

def fetch_pini_recent_videos():
    """
    Fetches the latest videos uploaded by Pini Barel on the 'Sport BeEychut Gvoha' channel.
    Returns a list of dicts: [{title, link, published_date, video_id}]
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        resp = requests.get(RSS_URL, headers=headers, timeout=10)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except Exception as e:
        logger.warning(f"Failed to fetch Pini Barel YouTube RSS feed: {e}")
        return []

    ns = {
        "atom": "http://www.w3.org/2005/Atom",
        "yt": "http://www.youtube.com/xml/schemas/2015"
    }

    videos = []
    for entry in root.findall("atom:entry", ns):
        try:
            title = entry.find("atom:title", ns).text or ""
            link_elem = entry.find("atom:link", ns)
            link = link_elem.attrib.get("href") if link_elem is not None else ""
            published = entry.find("atom:published", ns).text or ""
            video_id_elem = entry.find("yt:videoId", ns)
            video_id = video_id_elem.text if video_id_elem is not None else ""

            # Date format in Atom: 2026-10-08T06:12:34+00:00
            pub_date = published[:10] if len(published) >= 10 else ""

            videos.append({
                "title": title,
                "link": link,
                "video_id": video_id,
                "published_date": pub_date,
                "published_full": published
            })
        except Exception:
            continue

    return videos

def match_game_to_pini_video(game, videos, opponent_hebrew_keywords=None):
    """
    Checks if a given game has an associated video summary on Pini Barel's channel.
    """
    game_date_il = game.get("date_il") # YYYY-MM-DD
    opp_name = game.get("opponent", {}).get("name", "").lower()
    opp_abbrev = game.get("opponent", {}).get("abbrev", "").upper()

    # Dates to check: game day, and up to 3 days after the game
    candidate_dates = []
    try:
        dt = datetime.strptime(game_date_il, "%Y-%m-%d")
        for delta in range(0, 4):
            candidate_dates.append((dt + timedelta(days=delta)).strftime("%Y-%m-%d"))
    except Exception:
        candidate_dates = [game_date_il]

    keywords = []
    if opponent_hebrew_keywords:
        keywords.extend(opponent_hebrew_keywords)
    if opp_name:
        keywords.append(opp_name)

    # General player/team keywords for Pini Barel
    game_players = [p.get("name_he", "") for p in game.get("players", [])]
    if not game_players and "deni_status" in game:
        game_players = ["דני אבדיה", "אבדיה"]

    for vid in videos:
        title = vid.get("title", "")
        title_lower = title.lower()
        vid_date = vid.get("published_date")

        # Check date proximity
        if vid_date not in candidate_dates:
            continue

        # Check if opponent is mentioned in title
        opp_found = False
        for kw in keywords:
            if kw.lower() in title_lower:
                opp_found = True
                break

        # Check if Israeli player or #מעקבדיה is in title
        player_or_tag_found = any(p.split()[-1] in title for p in game_players if p) or "מעקבדיה" in title or "אבדיה" in title

        if opp_found and player_or_tag_found:
            return {
                "has_summary": True,
                "video_title": title,
                "video_url": vid.get("link"),
                "published_date": vid_date,
                "channel_url": CHANNEL_URL
            }

    return {
        "has_summary": False,
        "video_title": "",
        "video_url": "",
        "published_date": "",
        "channel_url": CHANNEL_URL
    }

if __name__ == "__main__":
    vids = fetch_pini_recent_videos()
    print(f"Fetched {len(vids)} recent videos from Pini Barel:")
    for v in vids[:5]:
        print(f"[{v['published_date']}] {v['title']} -> {v['link']}")
