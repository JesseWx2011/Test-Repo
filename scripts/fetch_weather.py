import os
import requests

CLIENT_ID = os.getenv("wgE96YE3scTQLKjnqiMsv")
CLIENT_SECRET = os.getenv("SVG2gQFV8y9DjKR0BRY9wPoSLvrMrIqF9Lq2IYaY")
BASE_URL = f"https://maps.aerisapi.com/{CLIENT_ID}_{CLIENT_SECRET}"

# Save file helper
def save_image(url, path):
    r = requests.get(url, timeout=20)
    if r.status_code == 200:
        with open(path, "wb") as f:
            f.write(r.content)
        print(f"Saved {path}")
    else:
        print(f"Failed to fetch {url}")

# Fetch radar composite
save_image(f"{BASE_URL}/radar/800x800/(30.63,-87.04),10/current.png",
           "api/radar/composite_latest.png")

# Fetch HRRR model frame 0
save_image(f"{BASE_URL}/models-hrrr/800x800/(30.63,-87.04),10/current.png",
           "api/models/hrrr/latest_0.png")

# You can loop for multiple frames using forecast steps:
for i in range(1, 6):  # get 5 frames
    save_image(f"{BASE_URL}/models-hrrr/800x800/(30.63,-87.04),10/{i*3}hr.png",
               f"api/models/hrrr/latest_{i}.png")