#!/usr/bin/env python3
import os, sys, json, requests, datetime as dt
from typing import List, Dict, Any, Optional

# -----------------------------
# Config / Inputs
# -----------------------------
API_TWC = os.getenv("API_TWC")
if not API_TWC:
    raise ValueError("Missing API_TWC (Weather.com) key in environment.")

# For now, hardcode test point; later parse CLI args.
LAT = os.getenv("BLEND_LAT", "33.51")
LON = os.getenv("BLEND_LON", "-95.14")

OUT_DIR = "api/forecast"
os.makedirs(OUT_DIR, exist_ok=True)

# -----------------------------
# Helpers
# -----------------------------
def _req_json(url: str, params: dict = None, timeout: int = 20) -> Any:
    r = requests.get(url, params=params, timeout=timeout, headers={"User-Agent":"JesseWeatherBlend/1.0"})
    r.raise_for_status()
    return r.json()

def get_nws_point(lat: str, lon: str) -> dict:
    url = f"https://api.weather.gov/points/{lat},{lon}"
    return _req_json(url)

def get_nws_forecast(lat: str, lon: str) -> dict:
    meta = get_nws_point(lat, lon)
    fcst_url = meta["properties"]["forecast"]  # day/night periods
    # Optionally also: meta["properties"]["forecastHourly"]
    return _req_json(fcst_url)

def parse_nws_periods(nws_json: dict) -> List[dict]:
    periods = nws_json.get("properties", {}).get("periods", [])
    out = []
    for p in periods:
        out.append({
            "name": p.get("name"),
            "start": p.get("startTime"),
            "end": p.get("endTime"),
            "is_day": p.get("isDaytime"),
            "temp": p.get("temperature"),
            "temp_unit": p.get("temperatureUnit"),
            "pop": (p.get("probabilityOfPrecipitation") or {}).get("value"),
            "wind_speed": p.get("windSpeed"),
            "wind_dir": p.get("windDirection"),
            "short": p.get("shortForecast"),
            "detail": p.get("detailedForecast"),
            "icon": p.get("icon"),
        })
    return out

def get_twc_daily(lat: str, lon: str, api_key: str) -> dict:
    url = "https://api.weather.com/v3/wx/forecast/daily/15day"
    params = {
        "geocode": f"{lat},{lon}",
        "format": "json",
        "units": "e",          # english / imperial
        "language": "en-US",
        "apiKey": api_key
    }
    return _req_json(url, params=params)

def parse_twc_daily(twc: dict) -> List[dict]:
    # TWC returns parallel arrays; zip across them safely
    days = []
    # Required arrays (guard for missing)
    v_utc = twc.get("validTimeUtc", [])
    daynames = twc.get("dayOfWeek", [])
    tmax = twc.get("temperatureMax", [])
    tmin = twc.get("temperatureMin", [])
    qpf = twc.get("qpf", [])
    narrative = twc.get("narrative", [])
    # We'll grab only length of validTimeUtc
    n = len(v_utc)
    for i in range(n):
        ts_utc = v_utc[i]
        try:
            date_utc = dt.datetime.utcfromtimestamp(ts_utc)
        except Exception:
            date_utc = None
        days.append({
            "date_utc": date_utc.isoformat() + "Z" if date_utc else None,
            "dow": daynames[i] if i < len(daynames) else None,
            "tmax": tmax[i] if i < len(tmax) else None,
            "tmin": tmin[i] if i < len(tmin) else None,
            "qpf": qpf[i] if i < len(qpf) else None,
            "narr": narrative[i] if i < len(narrative) else None,
        })
    return days

def _day_key_from_iso(iso: str) -> Optional[str]:
    # iso: "2025-07-18T14:00:00-05:00" -> return date portion in UTC? local? We'll use date part of ISO string's first 10 chars.
    if not iso:
        return None
    return iso[:10]

def _day_key_from_utcstamp_iso(iso: str) -> Optional[str]:
    if not iso:
        return None
    return iso[:10]

def collapse_nws_to_daily(nws_periods: List[dict]) -> Dict[str, dict]:
    """
    Collapse alternating day/night NWS periods into daily summary:
    choose max temp from day; min temp from night; max PoP; combine narratives.
    Keyed by start-date of daytime period (local string).
    """
    daily = {}
    for p in nws_periods:
        day_key = _day_key_from_iso(p["start"])
        if not day_key:
            continue
        d = daily.setdefault(day_key, {
            "nws_day_name": None,
            "nws_day_temp": None,
            "nws_night_temp": None,
            "nws_pop": 0,
            "nws_icon_day": None,
            "nws_icon_night": None,
            "nws_narr_day": "",
            "nws_narr_night": "",
        })
        # choose name if daytime
        if p["is_day"]:
            d["nws_day_name"] = p["name"]
            d["nws_day_temp"] = p["temp"]
            d["nws_icon_day"] = p["icon"]
            if p["detail"]:
                d["nws_narr_day"] = p["detail"]
        else:
            d["nws_night_temp"] = p["temp"]
            d["nws_icon_night"] = p["icon"]
            if p["detail"]:
                d["nws_narr_night"] = p["detail"]
        # update PoP max
        if isinstance(p["pop"], (int, float)) and p["pop"] is not None:
            d["nws_pop"] = max(d["nws_pop"], p["pop"] or 0)
    return daily

def blend_days(nws_daily: Dict[str, dict], twc_days: List[dict], days_limit=7) -> List[dict]:
    """
    Build blended 7-day list. Use TWC date_utc keys and try to match NWS keys by date (best-effort).
    """
    blended = []
    for td in twc_days[:days_limit]:
        # Day key from TWC UTC datetime
        day_key = td["date_utc"][:10] if td["date_utc"] else None
        nws_match = nws_daily.get(day_key, {})
        # choose hi/lo
        hi = nws_match.get("nws_day_temp", td["tmax"])
        lo = nws_match.get("nws_night_temp", td["tmin"])
        # PoP blend: conservative max of NWS & (approx) TWC QPF>0? We'll just carry NWS PoP; you can refine.
        pop = nws_match.get("nws_pop")
        # Narrative: prefer NWS day+night stitched; else TWC narrative
        narr = ""
        if nws_match.get("nws_narr_day") or nws_match.get("nws_narr_night"):
            narr = (nws_match.get("nws_narr_day") or "").strip()
            night = (nws_match.get("nws_narr_night") or "").strip()
            if night:
                narr = narr + " " + night
        else:
            narr = td["narr"] or ""
        blended.append({
            "date": day_key,
            "dayOfWeek": td["dow"],
            "highTemp_F": hi,
            "lowTemp_F": lo,
            "qpf_in": td["qpf"],     # from TWC
            "pop_pct": pop,
            "narrative": narr,
            "icons": {
                "day": nws_match.get("nws_icon_day"),
                "night": nws_match.get("nws_icon_night")
            },
            "sourceFlags": {
                "nwsTempDay": nws_match.get("nws_day_temp") is not None,
                "nwsTempNight": nws_match.get("nws_night_temp") is not None,
                "nwsPoP": nws_match.get("nws_pop") is not None,
                "twcQpf": td["qpf"] is not None,
                "twcBase": True
            }
        })
    return blended

def build_payload(lat: str, lon: str, nws_json: dict, twc_json: dict) -> dict:
    nws_periods = parse_nws_periods(nws_json)
    nws_daily = collapse_nws_to_daily(nws_periods)
    twc_days = parse_twc_daily(twc_json)
    blended7 = blend_days(nws_daily, twc_days, days_limit=7)
    payload = {
        "metadata": {
            "generated_at": dt.datetime.utcnow().isoformat() + "Z",
            "lat": float(lat),
            "lon": float(lon),
            "units": "imperial",
            "sources": ["NWS", "TWC"],
            "days": len(blended7)
        },
        "days": blended7
    }
    return payload

def main():
    print(f"Blending NWS + TWC 7-day for {LAT},{LON}...")
    nws_json = get_nws_forecast(LAT, LON)
    twc_json = get_twc_daily(LAT, LON, API_TWC)
    out_payload = build_payload(LAT, LON, nws_json, twc_json)

    outfile = os.path.join(OUT_DIR, f"7day_{LAT}_{LON}.json")
    with open(outfile, "w") as f:
        json.dump(out_payload, f, indent=2)
    print(f" Saved blended forecast: {outfile}")

if __name__ == "__main__":
    main()
