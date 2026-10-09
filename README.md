# 🏀 Deni Avdija Israeli TV & Game Tracker
### מעקב שידורי ערוץ הספורט עבור משחקי דני אבדיה ופורטלנד טרייל בלייזרס

A daily automated tracker that monitors **Portland Trail Blazers** NBA games, matches them against live **Israeli TV broadcast schedules** (Sport 5 channels: 5SPORT, 5PLUS, 5LIVE, 5STARS, 5MAX, and Charlton Sport 1-4), and tracks **Deni Avdija's playing and injury status** using team reports (including **@TrailBlazersPR** on X).

---

## 🌟 Key Features

1. **Israeli TV Guide Ingestion (Sport 5 Network & Partners)**:
   * Scrapes real-time broadcast sheets from Sport 5 (`5SPORT / ערוץ 5`, `5PLUS / 5 פלוס`, `5LIVE`, `5STARS`, `5MAX`, `ספורט 1-4`).
   * Automatically detects live broadcasts and assigns the exact Israeli channel for each Portland game.
2. **Accurate Israel Time Conversion (IST/IDT)**:
   * Automatically converts UTC/US game times to local Israel Time, accounting for date shifts (e.g. night games in the US playing at 05:00 AM the next day in Israel).
3. **Deni Avdija Playing & Injury Status**:
   * **Tier 1 (Fastest updates)**: Ingestion support for the Portland Trail Blazers PR X account (**@TrailBlazersPR**), which posts official injury reports directly before games.
   * **Tier 2 (Continuous 24/7)**: Direct integration with ESPN and NBA Official Roster/Injury feeds (tracking active status, day-to-day, questionable, doubtful, and out).
4. **Dual Interface**:
   * **Terminal / CLI View**: Clear table with dates, Israeli times, matchups, channels, and Deni's status.
   * **Interactive Web Dashboard (`dashboard/index.html`)**: Modern, responsive dark-mode dashboard with countdown clocks, team logos, live badges, and filtering.
5. **Daily Automation**:
   * Windows Task Scheduler script (`setup_daily_task.ps1`) to automatically sync daily at 07:00 AM IST.

---

## 📂 Project Structure

```
c:\Apps\NBA Channel 5 tracker\
│
├── config.json                 # Configuration (team, player, timezone, X account)
├── run_tracker.py              # Main execution script
├── tracker.bat                 # One-click Windows runner
├── open_dashboard.bat          # One-click launcher for the visual dashboard
├── setup_daily_task.ps1        # Script to register daily automatic sync in Windows
│
├── tracker/
│   ├── fetch_schedule.py       # NBA Portland schedule fetcher
│   ├── fetch_tv_guide.py       # Sport 5 broadcast schedule scraper
│   ├── fetch_injury_status.py  # Deni Avdija injury engine (@TrailBlazersPR & ESPN)
│   └── matcher.py              # Correlates schedule + TV channels + player status
│
├── data/
│   └── games.json              # Local normalized JSON database
│
└── dashboard/
    └── index.html              # Responsive interactive dashboard
```

---

## 🚀 Quick Start

### 1. Run Tracker (Terminal Update)
Double-click [`tracker.bat`](file:///c:/Apps/NBA%20Channel%205%20tracker/tracker.bat) or run:
```powershell
python run_tracker.py
```

### 2. View Web Dashboard
Double-click [`open_dashboard.bat`](file:///c:/Apps/NBA%20Channel%205%20tracker/open_dashboard.bat) or open:
[`dashboard/index.html`](file:///c:/Apps/NBA%20Channel%205%20tracker/dashboard/index.html) in your browser.

### 3. Setup Daily Automatic Updates
To have Windows automatically update the schedule every morning at 07:00 AM IST:
1. Open PowerShell.
2. Run:
```powershell
powershell -ExecutionPolicy Bypass -File .\setup_daily_task.ps1
```

---

## ⚙️ Configuration (`config.json`)

You can customize settings in [`config.json`](file:///c:/Apps/NBA%20Channel%205%20tracker/config.json):
* `timezone`: `"Asia/Jerusalem"` (Israel Time)
* `tv_guide.days_ahead`: Number of days to scrape ahead (default: `10`)
* `x_twitter.account`: `"TrailBlazersPR"`
* `x_twitter.bearer_token`: (Optional) If you have an X/Twitter API Bearer Token, add it here for direct X API v2 queries. The tracker also supports public syndication and official NBA roster fallbacks.
