import logging
from datetime import datetime
from typing import Optional

import requests

from app.config import settings

logger = logging.getLogger("gatekeepify.lastfm")

BASE_URL = "https://ws.audioscrobbler.com/2.0/"


def get_artist_weekly_listeners(
    artist_name: str,
) -> Optional[list[dict]]:
    if not settings.lastfm_api_key:
        logger.warning("LASTFM_API_KEY is not set")
        return None

    logger.info(f"Fetching Last.fm data for '{artist_name}' with key '{settings.lastfm_api_key[:4]}...'")

    try:
        charts_resp = requests.get(
            BASE_URL,
            params={
                "method": "artist.getWeeklyChartList",
                "artist": artist_name,
                "api_key": settings.lastfm_api_key,
                "format": "json",
            },
            timeout=10,
        )
        logger.info(f"Last.fm chart list response: {charts_resp.status_code}")
        charts_resp.raise_for_status()
        chart_json = charts_resp.json()
        charts = chart_json.get("weeklychartlist", {}).get("chart", [])
        logger.info(f"Last.fm returned {len(charts)} chart periods")

        if not charts:
            return None

        recent_charts = charts[-52:]

        monthly: dict[str, int] = {}
        for chart in recent_charts:
            from_ts = int(chart["from"])
            chart_date = datetime.utcfromtimestamp(from_ts)
            month_key = chart_date.strftime("%Y-%m")

            detail_resp = requests.get(
                BASE_URL,
                params={
                    "method": "artist.getWeeklyPlaycountChart",
                    "artist": artist_name,
                    "from": chart["from"],
                    "to": chart["to"],
                    "api_key": settings.lastfm_api_key,
                    "format": "json",
                },
                timeout=10,
            )

            if detail_resp.status_code == 200:
                playcount_data = detail_resp.json()
                playcount = 0
                weekly_chart = playcount_data.get("weeklyartistchart", {})
                if weekly_chart:
                    artist_entries = weekly_chart.get("artist", [])
                    if isinstance(artist_entries, dict):
                        artist_entries = [artist_entries]
                    for entry in artist_entries:
                        if entry.get("name", "").lower() == artist_name.lower():
                            playcount = int(entry.get("playcount", 0))
                            break

                monthly[month_key] = monthly.get(month_key, 0) + playcount

        if not any(v > 0 for v in monthly.values()):
            info_resp = requests.get(
                BASE_URL,
                params={
                    "method": "artist.getInfo",
                    "artist": artist_name,
                    "api_key": settings.lastfm_api_key,
                    "format": "json",
                },
                timeout=10,
            )
            if info_resp.status_code == 200:
                info = info_resp.json().get("artist", {})
                stats = info.get("stats", {})
                total_listeners = int(stats.get("listeners", 0))
                total_playcount = int(stats.get("playcount", 0))
                return [{
                    "source": "lastfm_summary",
                    "total_listeners": total_listeners,
                    "total_playcount": total_playcount,
                }]

        return [
            {"month": m, "listen_count": c}
            for m, c in sorted(monthly.items())
            if c > 0
        ]

    except Exception as e:
        logger.error(f"Last.fm API error for '{artist_name}': {type(e).__name__}: {e}")
        return None
