#!/usr/bin/env python3
"""
blend_forecast.py
Fetch NWS + TWC forecast data for a point (lat,lon) and write a blended 7-day JSON.

Environment Variables:
  BLEND_LAT    Latitude (string or float)
  BLEND_LON    Longitude (string or float)
  API_TWC      Weather.com API key (required)
  DAYS_LIMIT   Optional (# of days to output; default 7)

Output:
  api/forecast/<lat>_<lon>_7day.json
"""
import os
import json
import requests
import datetime as dt
from typing import Any, Dict, List

# ---------------- Config from ENV ----------------
LAT = os.getenv("BLEND_LAT", "33.51")
LON = os.getenv("BLEND_LON", "-95.14")
API_TWC = os.getenv("API_TWC")
DAYS_LIMIT = int(os.getenv("DAYS_LIMIT", "7"))

if not API_TWC:
    raise ValueError("API_TWC not set in environment.")

OUT_DIR = "api/forecast"
os.makedirs(OUT_DIR, exist_ok=True)

def safe_coord_str(coord: str) -> str:
    """Format coord string into filesystem-safe segment: 33.51 -> 33_51 ; -95.14 -> -95_14."""
    return coord.strip().replace('.', '_')

SAFE_LAT = safe_coord_str(LAT)
SAFE_LON = safe_coord_str(LON)
OUT_FILE = os.path.join(OUT_DIR, f"{SAFE_LAT}_{SAFE_LON}_7day.json")

# ---------------- HTTP Helper ----------------
HEADERS = {"User-Agent": "JesseWx-BlendForecast/1.0 (+github)"}

def _req_json(url: str, params: Dict[str, Any] = None, timeout: int = 20) -> Any:
    r = requests.get(url, params=params, timeout=timeout, headers=HEADERS)
    r.raise_for_status()
    return r.json()

# ---------------- TWC Daily Forecast ----------------
def fetch_twc_daily(lat: str, lon: str, api_key: str) -> dict:
    url = "https://api.weather.com/v3/wx/forecast/daily/15day"
    params = {
        "geocode": f"{lat},{lon}",
        "format": "json",
        "units": "e",
        "language": "en-US",
        "apiKey": api_key
    }
    print(f"[TWC] {url}?geocode={lat},{lon}")
    return _req_json(url, params=params)

def parse_twc_daily(raw: dict, days: int) -> List[dict]:
    # arrays
    vutc = raw.get("validTimeUtc", [])
    dow = raw.get("dayOfWeek", [])
    tmax = raw.get("temperatureMax", [])
    tmin = raw.get("temperatureMin", [])
    narr = raw.get("narrative", [])
    qpf  = raw.get("qpf", [])

    out = []
    for i, ts in enumerate(vutc[:days]):
        try:
            dt_utc = dt.datetime.utcfromtimestamp(ts).isoformat() + "Z"
        except Exception:
            dt_utc = None
        out.append({
            "validTimeUtc": ts,
            "validTimeIso": dt_utc,
            "dayOfWeek": dow[i] if i < len(dow) else None,
            "tempMax_F": tmax[i] if i < len(tmax) else None,
            "tempMin_F": tmin[i] if i < len(tmin) else None,
            "qpf_in": qpf[i] if i < len(qpf) else None,
            "narrative": narr[i] if i < len(narr) else None,
        })
    return out

# ---------------- NWS Forecast ----------------
def fetch_nws_point(lat: str, lon: str) -> dict:
    url = f"https://api.weather.gov/points/{lat},{lon}"
    print(f"[NWS] {url}")
    return _req_json(url)

def fetch_nws_forecast(lat: str, lon: str) -> dict:
    meta = fetch_nws_point(lat, lon)
    fcst_url = meta["properties"]["forecast"]  # day/night periods
    print(f"[NWS] Forecast URL: {fcst_url}")
    return _req_json(fcst_url)

def parse_nws_periods(raw: dict, days: int) -> List[dict]:
    # Raw day/night periods — we'll just pass them through (caller can merge later)
    periods = raw.get("properties", {}).get("periods", [])
    # Keep only what fits roughly in days*2 periods
    return periods[:days*2]

# ---------------- Blend / Package ----------------
def build_payload(lat: str, lon: str, twc_raw: dict, nws_raw: dict, days: int) -> dict:
    twc_days = parse_twc_daily(twc_raw, days)
    nws_periods = parse_nws_periods(nws_raw, days)

    payload = {
        "metadata": {
            "generated_at": dt.datetime.utcnow().isoformat() + "Z",
            "lat": float(lat),
            "lon": float(lon),
            "days_requested": days,
            "sources": ["TWC", "NWS"],
            "attribution": {
                "TWC": "Data courtesy The Weather Company / weather.com",
                "NWS": "Data courtesy National Weather Service"
            }
        },
        "twc_daily": twc_days,
        "nws_periods": nws_periods
    }
    return payload

def main():
    try:
        twc_data = fetch_twc_daily(LAT, LON, API_TWC)
    except Exception as e:
        print(f"!! Error fetching TWC: {e}")
        twc_data = {}

    try:
        nws_data = fetch_nws_forecast(LAT, LON)
    except Exception as e:
        print(f"!! Error fetching NWS: {e}")
        nws_data = {"properties":{"periods":[]} }

    blended = build_payload(LAT, LON, twc_data, nws_data, DAYS_LIMIT)

    with open(OUT_FILE, "w") as f:
        json.dump(blended, f, indent=2)
    print(f"✔ Wrote {OUT_FILE}")

if __name__ == "__main__":
    main()
