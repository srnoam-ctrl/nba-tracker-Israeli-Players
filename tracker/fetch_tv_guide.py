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

CHANNEL_INFO_REGISTRY = {
    "5SPORT": {
        "channel_code": "5SPORT",
        "display_name": "5SPORT (ערוץ 5)",
        "number_info": "אפיק 55",
        "is_free_tier": True,
        "tier_name": "ערוץ פתוח בסיסי (בחינם בכל החבילות)",
        "tier_badge": "🟢 ערוץ פתוח לכולם (אפיק 55)",
        "tier_type": "FREE"
    },
    "5PLUS": {
        "channel_code": "5PLUS",
        "display_name": "5PLUS (ערוץ 5 פלוס)",
        "number_info": "אפיק 56",
        "is_free_tier": True,
        "tier_name": "ערוץ פתוח בסיסי (בחבילת הבסיס)",
        "tier_badge": "🟢 ערוץ פתוח לכולם (אפיק 56)",
        "tier_type": "FREE"
    },
    "5LIVE": {
        "channel_code": "5LIVE",
        "display_name": "5LIVE (ערוץ 5 לייב)",
        "number_info": "אפיק 58",
        "is_free_tier": False,
        "tier_name": "ערוץ בתשלום נוסף (חבילת פרימיום)",
        "tier_badge": "🔒 ערוץ בתשלום (אפיק 58)",
        "tier_type": "PAID"
    },
    "5STARS": {
        "channel_code": "5STARS",
        "display_name": "5STARS (ערוץ 5 כוכבים)",
        "number_info": "אפיק 59",
        "is_free_tier": False,
        "tier_name": "ערוץ בתשלום נוסף (חבילת פרימיום)",
        "tier_badge": "🔒 ערוץ בתשלום (אפיק 59)",
        "tier_type": "PAID"
    },
    "5GOLD": {
        "channel_code": "5GOLD",
        "display_name": "5GOLD (ערוץ 5 גולד)",
        "number_info": "אפיק 57",
        "is_free_tier": False,
        "tier_name": "ערוץ בתשלום נוסף (חבילת פרימיום)",
        "tier_badge": "🔒 ערוץ בתשלום (אפיק 57)",
        "tier_type": "PAID"
    },
    "5MAX": {
        "channel_code": "5MAX",
        "display_name": "5MAX (ערוץ 5 מקס)",
        "number_info": "אפיק 60",
        "is_free_tier": False,
        "tier_name": "ערוץ בתשלום נוסף",
        "tier_badge": "🔒 ערוץ בתשלום (אפיק 60)",
        "tier_type": "PAID"
    },
    "5SPORT 4K": {
        "channel_code": "5SPORT 4K",
        "display_name": "5SPORT 4K",
        "number_info": "אפיק 555",
        "is_free_tier": False,
        "tier_name": "ערוץ 4K בתשלום נוסף",
        "tier_badge": "🔒 ערוץ 4K בתשלום (אפיק 555)",
        "tier_type": "PAID"
    },
    "5MOBILE": {
        "channel_code": "5MOBILE",
        "display_name": "5MOBILE (אתר ואפליקציה)",
        "number_info": "אתר / אפליקציה",
        "is_free_tier": True,
        "tier_name": "שידור דיגיטלי באתר ובאפליקציה",
        "tier_badge": "📱 שידור דיגיטלי (אתר/אפליקציה)",
        "tier_type": "DIGITAL"
    }
}

def resolve_channel_details(raw_name):
    """
    Resolves raw Sport5 channel string or alt tag to accurate channel metadata including Free vs Paid tier.
    """
    if not raw_name:
        return CHANNEL_INFO_REGISTRY["5SPORT"]
    
    cleaned = raw_name.strip()
    lower = cleaned.lower()

    if "live" in lower or "לייב" in lower:
        return CHANNEL_INFO_REGISTRY["5LIVE"]
    if "stars" in lower or "כוכבים" in lower:
        return CHANNEL_INFO_REGISTRY["5STARS"]
    if "gold" in lower or "גולד" in lower:
        return CHANNEL_INFO_REGISTRY["5GOLD"]
    if "max" in lower or "מקס" in lower:
        return CHANNEL_INFO_REGISTRY["5MAX"]
    if "4k" in lower:
        return CHANNEL_INFO_REGISTRY["5SPORT 4K"]
    if "5+" in lower or "פלוס" in lower or "plus" in lower:
        return CHANNEL_INFO_REGISTRY["5PLUS"]
    if "מובייל" in lower or "mobile" in lower:
        return CHANNEL_INFO_REGISTRY["5MOBILE"]
    if any(k in lower for k in ["ספורט 1", "ספורט 2", "ספורט 3", "ספורט 4"]):
        ch_num = [k for k in ["ספורט 1", "ספורט 2", "ספורט 3", "ספורט 4"] if k in lower]
        ch_label = ch_num[0] if ch_num else "צ'רלטון"
        return {
            "channel_code": "CHARLTON",
            "display_name": f"{ch_label} (Charlton)",
            "number_info": "אפיקי צ'רלטון",
            "is_free_tier": False,
            "tier_name": "ערוץ צ'רלטון בתשלום נפרד",
            "tier_badge": f"🔒 {ch_label} בתשלום",
            "tier_type": "PAID"
        }
    if "ערוץ הספורט" in lower or "ספורט 5" in lower or "5sport" in lower or "ערוץ 5" in lower:
        return CHANNEL_INFO_REGISTRY["5SPORT"]

    return {
        "channel_code": "OTHER",
        "display_name": cleaned,
        "number_info": "",
        "is_free_tier": False,
        "tier_name": "ערוץ ספורט",
        "tier_badge": cleaned,
        "tier_type": "OTHER"
    }

def normalize_channel_name(raw_name):
    return resolve_channel_details(raw_name)["display_name"]

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
    current_channel_details = CHANNEL_INFO_REGISTRY["5SPORT"]
    current_channel = current_channel_details["display_name"]

    for tr in rows:
        # Check if header row defining channel
        if "tr-header" in tr.get("class", []):
            img = tr.find("img")
            span = tr.find("span", class_="channel-text")
            raw_channel = ""
            if img and img.get("alt"):
                raw_channel = img.get("alt")
            elif img and img.get("title"):
                raw_channel = img.get("title")
            elif span:
                raw_channel = span.get_text(strip=True)

            current_channel_details = resolve_channel_details(raw_channel)
            current_channel = current_channel_details["display_name"]
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
                    "channel_details": current_channel_details,
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
