import os
import requests
import json
from datetime import datetime

API_TWC = os.getenv("API_TWC")
if not API_TWC:
    raise ValueError("Missing API_TWC secret")

BASE_URL = "https://api.weather.com/v3/tropical/cone"
PARAMS = {
    "source": "default",
    "basin": "WP",           # You can loop through all basins if needed
    "language": "en-US",
    "format": "json",
    "units": "e",
    "nautical": "true",
    "apiKey": API_TWC
}

def fetch_tropical_data():
    resp = requests.get(BASE_URL, params=PARAMS, timeout=30)
    resp.raise_for_status()
    return resp.json()

def parse_storms(data):
    storms = {}
    features = data.get("features", [])
    
    for idx, feature in enumerate(features):
        p = feature["properties"]
        pos = p["currentPosition"]
        heading = pos.get("heading", {})
        
        # Compose position string with hemisphere
        lat = pos["latitude"]
        lat_hem = pos.get("latitudeHemisphere", "N")
        lon = pos["longitude"]
        lon_hem = pos.get("longitudeHemisphere", "E")
        position_str = f"{lat}°{lat_hem}, {lon}°{lon_hem}"
        
        # Compose storm JSON item
        storms[f"[{idx}]"] = {
            "basin": basin_full_name(p.get("basin")),
            "basinAbbreviation": p.get("basin"),
            "name": p.get("stormName") or p.get("alternateStormName") or "Unknown",
            "intensity": pos.get("stormType"),
            "intensityAbbreviation": pos.get("stormTypeCode"),
            "sustainedWinds": f"{pos.get('maximumSustainedWind', 0)} mph",
            "sustainedGusts": f"{pos.get('windGust', 0)} mph",
            "position": position_str,
            "movementSpeed": f"{heading.get('stormSpeed', 0)} mph",
            "lastUpdate": p.get("issueDateTime"),
            "issuedBy": p.get("source"),
            "issuedByFormal": issuing_agency_name(p.get("source")),
            "movementDirection": heading.get("stormDirection"),
            "movementCardinal": heading.get("stormDirectionCardinal"),
            "movementDegrees": heading.get("stormDirection"),
            "stormNumber": p.get("stormNumber"),
            "stormBaroPressure": pressure_in_inhg(pos.get("minimumPressure")),
            "stormBaroMillibars": pressure_in_mb(pos.get("minimumPressure")),
            "stormId": p.get("stormId"),
            "forecastCone": {
                "comment": "Sample Code, expect a bunch of pairs of coordinates here soon :)"
            },
            "apiCourtesy": "TWC, JesseLikesWeather"
        }
    return {"storms": storms}

def basin_full_name(abbrev):
    mapping = {
        "NA": "North Atlantic",
        "WP": "West Pacific",
        "EP": "East Pacific",
        "IO": "Indian Ocean",
        "SH": "Southern Hemisphere",
        "SP": "South Pacific"
    }
    return mapping.get(abbrev, "Unknown")

def issuing_agency_name(abbrev):
    mapping = {
        "NHC": "National Hurricane Center",
        "JTWC": "Joint Typhoon Warning Center",
        "CPHC": "Central Pacific Hurricane Center",
        "JMA": "Japan Meteorological Agency"
    }
    return mapping.get(abbrev, "Unknown")

def pressure_in_inhg(mb):
    if mb is None:
        return None
    inhg = float(mb) * 0.02953
    return f"{inhg:.2f} inHg"

def pressure_in_mb(mb):
    if mb is None:
        return None
    return f"{mb}mb"

def main():
    data = fetch_tropical_data()
    summary = parse_storms(data)
    with open("api/tropical_summary.json", "w") as f:
        json.dump(summary, f, indent=4)
    print("Tropical cyclone summary saved to api/tropical_summary.json")

if __name__ == "__main__":
    main()
