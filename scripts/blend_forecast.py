import os
import json
import requests
import urllib.parse

# Environment variables
twc_api_key = os.getenv("API_TWC")

# Coordinates from GitHub Action or default for local testing
lat = os.getenv("BLEND_LAT", "33.51")
lon = os.getenv("BLEND_LON", "-95.14")

# Encode coordinates for file naming
safe_lat = lat.replace('.', '_')
safe_lon = lon.replace('.', '_')

# Output path for API
output_dir = "api/forecast"
os.makedirs(output_dir, exist_ok=True)
output_file = f"{output_dir}/{safe_lat}_{safe_lon}_7day.json"

# --- Fetch TWC Forecast ---
twc_url = (
    f"https://api.weather.com/v3/wx/forecast/daily/15day"
    f"?geocode={lat},{lon}&format=json&units=e&language=en-US&apiKey={twc_api_key}"
)
print(f"Fetching TWC forecast from {twc_url}")
twc_response = requests.get(twc_url)
twc_data = twc_response.json()

# --- Fetch NWS Forecast ---
nws_point_url = f"https://api.weather.gov/points/{lat},{lon}"
print(f"Fetching NWS point data from {nws_point_url}")
point_response = requests.get(nws_point_url)
point_data = point_response.json()
forecast_url = point_data["properties"]["forecast"]

nws_forecast_response = requests.get(forecast_url)
nws_data = nws_forecast_response.json()

# --- Blend Logic ---
blended = {
    "location": {"lat": lat, "lon": lon},
    "source": ["TWC", "NWS"],
    "generated": nws_data["properties"].get("updateTime", ""),
    "forecast": {
        "twc": {
            "dayOfWeek": twc_data.get("dayOfWeek", []),
            "temperatureMax": twc_data.get("temperatureMax", []),
            "temperatureMin": twc_data.get("temperatureMin", []),
            "narrative": twc_data.get("narrative", [])
        },
        "nws": nws_data.get("properties", {}).get("periods", [])
    }
}

# Save blended forecast
with open(output_file, "w") as f:
    json.dump(blended, f, indent=4)

print(f" Blended forecast saved to {output_file}")
