#!/usr/bin/env python3
"""
build_forecast_index.py
Scan api/forecast/ for *_7day.json files and produce api/forecast/index.json
Structure:
{
  "generated_at": "...",
  "points": [
     {"lat": 33.51, "lon": -95.14, "url": "33_51_-95_14_7day.json"},
     ...
  ]
}
"""
import os
import json
import re
import datetime as dt

FORECAST_DIR = "api/forecast"
INDEX_FILE = os.path.join(FORECAST_DIR, "index.json")

# Pattern matches:  33_51_-95_14_7day.json
PAT = re.compile(r'^(-?\d+)_?(\d*)_(-?\d+)_?(\d*)_7day\.json$')

def unslug_to_float(whole: str, frac: str) -> float:
    """Convert whole='33', frac='51' -> 33.51 ; handles negatives properly."""
    sign = -1 if whole.startswith('-') else 1
    w = whole.lstrip('-')
    if frac:
        num = float(f"{w}.{frac}")
    else:
        num = float(w)
    return sign * num

def main():
    if not os.path.isdir(FORECAST_DIR):
        print(f"Forecast dir {FORECAST_DIR} not found; nothing to index.")
        return

    points = []
    for f in os.listdir(FORECAST_DIR):
        if not f.endswith("_7day.json"):
            continue
        m = PAT.match(f)
        if not m:
            continue
        lat_whole, lat_frac, lon_whole, lon_frac = m.groups()
        lat = unslug_to_float(lat_whole, lat_frac)
        lon = unslug_to_float(lon_whole, lon_frac)
        points.append({
            "lat": lat,
            "lon": lon,
            "url": f
        })

    out = {
        "generated_at": dt.datetime.utcnow().isoformat() + "Z",
        "points": points
    }

    with open(INDEX_FILE, "w") as fh:
        json.dump(out, fh, indent=2)
    print(f" Wrote index: {INDEX_FILE} ({len(points)} points)")

if __name__ == "__main__":
    main()
