import os
import requests
import json
from datetime import datetime

# Get API keys from environment variables
CLIENT_ID = os.getenv("AERIS_ID")
CLIENT_SECRET = os.getenv("AERIS_SECRET")

if not CLIENT_ID or not CLIENT_SECRET:
    raise ValueError("Missing Aeris API credentials. Add AERIS_ID and AERIS_SECRET as secrets.")

# Base Aeris URL
BASE_URL = f"https://maps.aerisapi.com/{CLIENT_ID}_{CLIENT_SECRET}"

# Paths for saving files
API_PATH = "api"
RADAR_PATH = os.path.join(API_PATH, "radar")
HRRR_PATH = os.path.join(API_PATH, "models", "hrrr")

# Ensure directories exist
os.makedirs(RADAR_PATH, exist_ok=True)
os.makedirs(HRRR_PATH, exist_ok=True)

# Milton, FL location and map settings
LAT, LON = 30.63, -87.04
IMAGE_SIZE = "800x800"
ZOOM = 7  # Adjust zoom as needed

def save_image(url, path):
    """Download an image and save it locally."""
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        with open(path, "wb") as f:
            f.write(r.content)
        print(f"✅ Saved: {path}")
    except Exception as e:
        print(f"❌ Failed to fetch {url}: {e}")

def save_json(data, path):
    """Save JSON data to a file."""
    with open(path, "w") as f:
        json.dump(data, f, indent=4)
    print(f"✅ Saved: {path}")

# ======================
# 1. Download Radar Composite
# ======================
radar_url = f"{BASE_URL}/radar/{IMAGE_SIZE}/({LAT},{LON}),{ZOOM}/current.png"
save_image(radar_url, os.path.join(RADAR_PATH, "composite_latest.png"))

# ======================
# 2. Download HRRR Rainfall Forecast Images
# ======================
forecast_hours = ["current", "+1hr", "+2hr", "+3hr"]
for i, hour in enumerate(forecast_hours):
    hrrr_url = f"{BASE_URL}/fqpf-accum-hrrr/{IMAGE_SIZE}/({LAT},{LON}),{ZOOM}/{hour}.png"
    save_image(hrrr_url, os.path.join(HRRR_PATH, f"latest_{i}.png"))

# ======================
# 3. Create forecast.json (placeholder)
# ======================
forecast_data = {
    "generated_at": datetime.utcnow().isoformat() + "Z",
    "location": {"lat": LAT, "lon": LON, "name": "Milton, FL"},
    "forecast": [
        {"time": "+0hr", "qpf": "current image: latest_0.png"},
        {"time": "+1hr", "qpf": "image: latest_1.png"},
        {"time": "+2hr", "qpf": "image: latest_2.png"},
        {"time": "+3hr", "qpf": "image: latest_3.png"}
    ]
}
save_json(forecast_data, os.path.join(API_PATH, "forecast.json"))

# ======================
# 4. Create alerts.json (placeholder)
# ======================
alerts_data = {
    "generated_at": datetime.utcnow().isoformat() + "Z",
    "alerts": []  # Future: fetch real alerts from Aeris or NWS CAP
}
save_json(alerts_data, os.path.join(API_PATH, "alerts.json"))

print("✅ All tasks completed!")