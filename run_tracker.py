import json
import logging
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

# Fix encoding for Windows terminals
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("Tracker")

from tracker.fetch_schedule import fetch_team_schedule
from tracker.fetch_tv_guide import fetch_tv_guide_range
from tracker.fetch_injury_status import get_player_status
from tracker.matcher import correlate_games_with_tv_and_status

def load_config():
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def run():
    config = load_config()
    tz_name = config.get("timezone", "Asia/Jerusalem")
    days_ahead = config.get("tv_guide", {}).get("days_ahead", 10)
    now_il = datetime.now(ZoneInfo(tz_name))

    print("=" * 115)
    print("🇮🇱  ALL ISRAELIS IN THE NBA - TV BROADCAST & GAME TRACKER")
    print(f"⏰  Current Israel Time: {now_il.strftime('%Y-%m-%d %H:%M:%S (%A)')}")
    print("=" * 115)

    # 1. Fetch Israeli Sports TV Guide (shared across all teams)
    print(f"\n[1/3] 📺 Scraping Israeli Sport 5 and sports TV guide ({days_ahead} days ahead)...")
    broadcasts = fetch_tv_guide_range(days_ahead=days_ahead, target_tz=tz_name)
    print(f"      -> Ingested {len(broadcasts)} Israeli broadcast entries.")

    # 2. Fetch Team Schedules (cache unique team slugs)
    players_config = config.get("players", [])
    unique_teams = list(set(p.get("team_slug", "por") for p in players_config))
    team_schedules = {}

    print(f"\n[2/3] 📡 Fetching NBA schedules for teams: {', '.join(unique_teams).upper()}...")
    for t in unique_teams:
        sched = fetch_team_schedule(team_slug=t, target_tz=tz_name)
        team_schedules[t] = sched
        print(f"      -> {t.upper()}: {len(sched)} games found.")

    # 3. Process each player
    print("\n[3/3] 🩺 Ingesting player statuses and correlating broadcasts...")
    processed_players = []
    all_games_map = {}

    for p in players_config:
        p_name = p.get("name")
        p_slug = p.get("team_slug")
        p_id = p.get("id")

        status = get_player_status(p, config=config)
        sched = team_schedules.get(p_slug, [])
        enriched = correlate_games_with_tv_and_status(sched, broadcasts, status, days_ahead_limit=7, team_slug=p_slug)

        player_data = {
            **p,
            "status": status,
            "total_games": len(enriched),
            "games": enriched,
            "next_game": enriched[0] if enriched else None
        }
        processed_players.append(player_data)

        # Merge games into unified chronological feed
        for g in enriched:
            g_id = g.get("id")
            if g_id not in all_games_map:
                all_games_map[g_id] = {
                    **g,
                    "players": [p]
                }
            else:
                all_games_map[g_id]["players"].append(p)

    # Sort all games by datetime
    all_games_list = list(all_games_map.values())
    all_games_list.sort(key=lambda x: x.get("utc_date", ""))

    # 4. Check for Pini Barel (@PiniBarel) 'מעקבדיה' YouTube video summaries
    print("\n[4/4] 🎥 Checking Pini Barel YouTube channel (@PiniBarel) for 'מעקבדיה' video summaries...")
    from tracker.fetch_pini_summaries import fetch_pini_recent_videos, match_game_to_pini_video
    from tracker.matcher import NBA_HEBREW_TEAMS

    pini_videos = fetch_pini_recent_videos()
    print(f"      -> Ingested {len(pini_videos)} recent videos from Pini Barel.")

    for g in all_games_list:
        opp_abbrev = g.get("opponent", {}).get("abbrev", "").upper()
        opp_kws = NBA_HEBREW_TEAMS.get(opp_abbrev, [])
        g["pini_summary"] = match_game_to_pini_video(g, pini_videos, opponent_hebrew_keywords=opp_kws)

    for p in processed_players:
        for g in p.get("games", []):
            opp_abbrev = g.get("opponent", {}).get("abbrev", "").upper()
            opp_kws = NBA_HEBREW_TEAMS.get(opp_abbrev, [])
            g["pini_summary"] = match_game_to_pini_video(g, pini_videos, opponent_hebrew_keywords=opp_kws)

    # 5. Extract Player Boxscores for completed games (with 48h spoiler logic)
    print("\n[5/5] 📊 Extracting player boxscores & 48-hour spoiler protections...")
    from tracker.fetch_game_stats import get_game_player_stats

    for g in all_games_list:
        g["player_boxscores"] = {}
        for p in g.get("players", []):
            st = get_game_player_stats(g, p)
            g["player_boxscores"][p.get("id")] = st
            if p.get("id") == "deni_avdija":
                g["player_boxscore"] = st

    for p in processed_players:
        for g in p.get("games", []):
            g["player_boxscore"] = get_game_player_stats(g, p)

    # Save to data/games.json and data/games_data.js
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)
    output_path = os.path.join(data_dir, "games.json")
    output_js_path = os.path.join(data_dir, "games_data.js")

    # Portland primary player for backward compatibility
    deni_player = next((p for p in processed_players if p.get("id") == "deni_avdija"), processed_players[0] if processed_players else {})

    output_payload = {
        "last_updated": now_il.isoformat(),
        "last_updated_display": now_il.strftime("%d/%m/%Y %H:%M:%S"),
        "pini_channel": {
            "channel_name": "ספורט באיכות גבוהה (פיני בראל)",
            "series_name": "מעקבדיה",
            "channel_url": "https://www.youtube.com/@PiniBarel",
            "total_recent_videos": len(pini_videos)
        },
        "players": processed_players,
        "all_games": all_games_list,
        # Backward compatibility fields
        "deni_status": deni_player.get("status", {}),
        "total_games": len(deni_player.get("games", [])),
        "games": deni_player.get("games", [])
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output_payload, f, indent=2, ensure_ascii=False)
    with open(output_js_path, "w", encoding="utf-8") as f:
        f.write("window.GAMES_DATA = " + json.dumps(output_payload, indent=2, ensure_ascii=False) + ";\n")
    print(f"💾 Updated multi-player database saved to: {output_path}")

    # Display console summary table
    print("\n" + "=" * 125)
    print("🏆  ISRAELI NBA PLAYERS STATUS OVERVIEW")
    print("-" * 125)
    for p in processed_players:
        st = p.get("status", {})
        next_g = p.get("next_game")
        next_info = f"{next_g.get('date_il')} {next_g.get('time_il')} vs {next_g.get('opponent', {}).get('name')}" if next_g else "None"
        ch = next_g.get("tv_broadcast", {}).get("channel_name", "TBD") if next_g else "N/A"
        print(f"• {p.get('name_he')} ({p.get('team_name_he')}, #{p.get('jersey')} {p.get('position')})")
        print(f"  Status: {st.get('status')} ({st.get('detail')}) | Source: {st.get('source')}")
        print(f"  Next Game: {next_info} | Channel: {ch}")
        print("-" * 125)

    print("\n" + "=" * 125)
    print(f"{'DATE (IST)':<12} {'TIME':<7} {'MATCHUP':<34} {'PLAYERS':<25} {'ISRAELI CHANNEL':<28} {'STATUS':<12}")
    print("-" * 125)
    for g in all_games_list[:15]:
        date_str = g.get("date_il")
        time_str = g.get("time_il")
        matchup = f"{g.get('away_team', {}).get('abbrev')} @ {g.get('home_team', {}).get('abbrev')} ({g.get('short_name')})"
        players_names = ", ".join([p.get("name_he") for p in g.get("players", [])])
        channel = g.get("tv_broadcast", {}).get("channel_name", "TBD")
        if len(channel) > 26:
            channel = channel[:25] + "…"
        st = g.get("player_status", {}).get("status", "Active")
        print(f"{date_str:<12} {time_str:<7} {matchup:<34} {players_names:<25} {channel:<28} {st:<12}")

    print("=" * 125)
    print("✨ Multi-player sync completed successfully!")
    return output_payload

if __name__ == "__main__":
    run()
