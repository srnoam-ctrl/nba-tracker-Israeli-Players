import logging
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

logger = logging.getLogger(__name__)

CHANNEL_MAPPINGS = {
    "ערוץ הספורט": "5SPORT (ערוץ 5)",
    "ספורט 5": "5SPORT (ערוץ 5)",
    "ספורט 5+": "5PLUS (ערוץ 5+)",
    "5+": "5PLUS (ערוץ 5+)",
    "ספורט 5 live": "5LIVE (ערוץ 5 לייב)",
    "ספורט live": "5LIVE (ערוץ 5 לייב)",
    "5 live": "5LIVE (ערוץ 5 לייב)",
    "5 stars": "5STARS (ערוץ 5 כוכבים)",
    "5stars": "5STARS (ערוץ 5 כוכבים)",
    "5max": "5MAX (ערוץ 5 מקס)",
    "ספורט gold": "5GOLD (ערוץ 5 גולד)",
    "ספורט 4k": "5SPORT 4K",
    "ספורט 1": "ספורט 1 (Charlton)",
    "ספורט 2": "ספורט 2 (Charlton)",
    "ספורט 3": "ספורט 3 (Charlton)",
    "ספורט 4": "ספורט 4 (Charlton)",
    "ספורט מובייל": "5MOBILE (אפליקציה/אתר)"
}

def normalize_channel_name(raw_name):
    if not raw_name:
        return "ערוץ הספורט"
    cleaned = raw_name.strip()
    lower = cleaned.lower()
    for key, val in CHANNEL_MAPPINGS.items():
        if key in lower:
            return val
    return cleaned

def fetch_daily_tv_sheet(date_str):
    """
    date_str: 'YYYY-M-D'
    Fetches the broadcast sheet from Sport 5.
    """
    url = f"https://www.sport5.co.il/Ajax/GetBroadcastSheetData.aspx?Type=&Date={date_str}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Referer": "https://www.sport5.co.il/html/pages/broadcastsheet.html"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=12)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        logger.warning(f"Failed to fetch Sport5 broadcast sheet for {date_str}: {e}")
        return ""

def parse_broadcast_sheet(html_content, date_str):
    """
    Parses the Sport 5 broadcast table into a list of broadcast entries.
    """
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, "html.parser")
    rows = soup.find_all("tr")
    
    broadcasts = []
    current_channel = "ערוץ הספורט"

    for tr in rows:
        # Check if header row defining channel
        if "tr-header" in tr.get("class", []):
            img = tr.find("img")
            span = tr.find("span", class_="channel-text")
            if img and img.get("alt"):
                current_channel = normalize_channel_name(img.get("alt"))
            elif img and img.get("title"):
                current_channel = normalize_channel_name(img.get("title"))
            elif span:
                current_channel = normalize_channel_name(span.get_text(strip=True))
            continue

        # Check for event rows
        date_td = tr.find("td", class_="date")
        text_td = tr.find("td", class_="text")

        if date_td and text_td:
            time_div = date_td.find("div")
            time_str = time_div.get_text(strip=True) if time_div else ""
            is_live = bool(date_td.find("img", alt="ישיר") or date_td.find("img", title="ישיר"))
            title = text_td.get_text(strip=True)

            if time_str and title:
                broadcasts.append({
                    "date": date_str,
                    "time": time_str,
                    "channel": current_channel,
                    "title": title,
                    "is_live": is_live
                })

    return broadcasts

def fetch_tv_guide_range(days_ahead=10, target_tz="Asia/Jerusalem"):
    """
    Scrapes Sport 5 broadcast sheets for the next `days_ahead` days.
    """
    tz = ZoneInfo(target_tz)
    now = datetime.now(tz)
    all_broadcasts = []

    for i in range(days_ahead):
        target_date = now + timedelta(days=i)
        # Sport 5 expects 'YYYY-M-D' without leading zeros
        date_param = f"{target_date.year}-{target_date.month}-{target_date.day}"
        iso_date = target_date.strftime("%Y-%m-%d")

        html = fetch_daily_tv_sheet(date_param)
        items = parse_broadcast_sheet(html, iso_date)
        all_broadcasts.extend(items)

    return all_broadcasts

if __name__ == "__main__":
    print("Fetching Israeli sports TV guide...")
    listings = fetch_tv_guide_range(days_ahead=3)
    print(f"Total broadcast items fetched: {len(listings)}")
    
    # Filter for basketball or NBA broadcasts
    bball = [b for b in listings if any(k in b["title"] for k in ["NBA", "פורטלנד", "דני", "אבדיה", "כדורסל", "יורוליג"])]
    print(f"Basketball/Relevant broadcasts found: {len(bball)}")
    for item in bball[:10]:
        print(f"[{item['date']} {item['time']}] {item['channel']} | Live: {item['is_live']} | {item['title']}")
