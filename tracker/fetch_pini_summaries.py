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

import json
import os

CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "pini_videos_cache.json")

def load_cached_videos():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read pini_videos_cache.json: {e}")
    return []

def save_cached_videos(videos):
    try:
        os.makedirs(os.path.dirname(CACHE_FILE), exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(videos, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"Failed to save pini_videos_cache.json: {e}")

def fetch_pini_recent_videos():
    """
    Fetches the latest videos uploaded by Pini Barel on the 'Sport BeEychut Gvoha' channel.
    Returns a list of dicts: [{title, link, published_date, video_id, thumbnail, is_nba}]
    Saves to and reads from persistent cache so videos are never lost.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/rss+xml, application/xml, text/xml, */*"
    }

    cached = load_cached_videos()
    cached_map = {v["video_id"]: v for v in cached if "video_id" in v}

    fetched_videos = []
    try:
        resp = requests.get(RSS_URL, headers=headers, timeout=15)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            ns = {
                "atom": "http://www.w3.org/2005/Atom",
                "yt": "http://www.youtube.com/xml/schemas/2015"
            }
            for entry in root.findall("atom:entry", ns):
                try:
                    title = entry.find("atom:title", ns).text or ""
                    link_elem = entry.find("atom:link", ns)
                    link = link_elem.attrib.get("href") if link_elem is not None else ""
                    published = entry.find("atom:published", ns).text or ""
                    video_id_elem = entry.find("yt:videoId", ns)
                    video_id = video_id_elem.text if video_id_elem is not None else ""

                    pub_date = published[:10] if len(published) >= 10 else ""

                    # Check if NBA / Maakavdiya related
                    title_lower = title.lower()
                    nba_kws = ["מעקבדיה", "אבדיה", "שרף", "וולף", "שארפ", "nba", "פורטלנד", "ברוקלין", "סקרמנטו", "בלייזרס", "נטס", "קינגס"]
                    is_nba = any(kw in title_lower for kw in nba_kws)

                    vid_data = {
                        "title": title,
                        "link": link,
                        "video_id": video_id,
                        "thumbnail": f"https://img.youtube.com/vi/{video_id}/mqdefault.jpg",
                        "published_date": pub_date,
                        "published_full": published,
                        "is_nba": is_nba
                    }
                    fetched_videos.append(vid_data)
                    cached_map[video_id] = vid_data
                except Exception:
                    continue
    except Exception as e:
        logger.warning(f"Failed to fetch Pini Barel YouTube RSS feed: {e}")

    # Combine cached and newly fetched, sorted by date descending
    all_videos = list(cached_map.values())
    all_videos.sort(key=lambda x: x.get("published_full", x.get("published_date", "")), reverse=True)

    if all_videos:
        save_cached_videos(all_videos)

    return all_videos

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
        player_or_tag_found = any(p.split()[-1] in title for p in game_players if p) or "מעקבדיה" in title or "אבדיה" in title or any(p in title for p in ["בן שרף", "דני וולף", "עמנואל שארפ", "דני אבדיה"])

        if opp_found and player_or_tag_found:
            return {
                "has_summary": True,
                "video_title": title,
                "video_url": vid.get("link"),
                "video_id": vid.get("video_id", ""),
                "thumbnail": vid.get("thumbnail") or f"https://img.youtube.com/vi/{vid.get('video_id', '')}/mqdefault.jpg",
                "published_date": vid_date,
                "channel_url": CHANNEL_URL
            }

    return {
        "has_summary": False,
        "video_title": "",
        "video_url": "",
        "video_id": "",
        "thumbnail": "",
        "published_date": "",
        "channel_url": CHANNEL_URL
    }

if __name__ == "__main__":
    vids = fetch_pini_recent_videos()
    print(f"Fetched {len(vids)} recent videos from Pini Barel:")
    for v in vids[:5]:
        print(f"[{v['published_date']}] {v['title']} -> {v['link']}")
