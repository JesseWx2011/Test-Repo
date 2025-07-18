/**
 * forecast-router.js
 * Usage:
 *   Include on a page that is loaded at /api/forecast/7day.json?lat=..&lon=..
 *   or call resolveForecast(lat, lon). Returns JSON for nearest prebuilt forecast.
 */

async function getQueryCoords() {
  const params = new URLSearchParams(window.location.search);
  const lat = parseFloat(params.get('lat'));
  const lon = parseFloat(params.get('lon'));
  if (isNaN(lat) || isNaN(lon)) return null;
  return { lat, lon };
}

async function fetchIndex() {
  const resp = await fetch('index.json', { cache: 'no-cache' });
  if (!resp.ok) throw new Error('Failed to load index.json');
  return resp.json();
}

function haversineMi(lat1, lon1, lat2, lon2) {
  const R = 3958.8; // miles
  const toRad = d => d * Math.PI / 180;
  const dlat = toRad(lat2 - lat1);
  const dlon = toRad(lon2 - lon1);
  const a = Math.sin(dlat/2)**2 + Math.cos(toRad(lat1))*Math.cos(toRad(lat2))*Math.sin(dlon/2)**2;
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
  return R * c;
}

function findNearestPoint(target, points) {
  let best = null;
  let bestDist = Infinity;
  for (const p of points) {
    const d = haversineMi(target.lat, target.lon, p.lat, p.lon);
    if (d < bestDist) {
      bestDist = d;
      best = { ...p, distance_mi: d };
    }
  }
  return best;
}

async function fetchForecastFile(url) {
  const resp = await fetch(url, { cache: 'no-cache' });
  if (!resp.ok) throw new Error(`Failed to load forecast file: ${url}`);
  return resp.json();
}

/**
 * Resolve forecast JSON for coordinates.
 * Returns: {metadata:{}, twc_daily:[], nws_periods:[]} or throws.
 */
export async function resolveForecast(lat, lon) {
  const idx = await fetchIndex();
  const nearest = findNearestPoint({lat, lon}, idx.points);
  if (!nearest) throw new Error('No forecast points available.');
  const data = await fetchForecastFile(nearest.url);
  data._router = {
    requested: {lat, lon},
    matched_point: nearest,
  };
  return data;
}

/* Demo when loaded in a browser directly */
(async function autoRunIfBrowser() {
  if (typeof window === 'undefined') return;
  const qc = await getQueryCoords();
  if (!qc) return; // no coords in URL, do nothing
  try {
    const data = await resolveForecast(qc.lat, qc.lon);
    // Render basic demo
    const pre = document.createElement('pre');
    pre.textContent = JSON.stringify(data, null, 2);
    document.body.appendChild(pre);
  } catch (err) {
    document.body.textContent = 'Error: ' + err.message;
  }
})();
