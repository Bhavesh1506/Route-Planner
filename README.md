# Route Fuel Planner API

A deliberately small Django 6.1 API for the Backend Django Engineer assessment. It accepts two US locations, obtains the driving route **once**, finds economical fuel stops from the supplied OPIS price list, and returns route GeoJSON that a frontend can render on a map.

## Why this design

- **Django 6.1** is the current stable Django release for this environment.
- **OSRM** is a free, no-key route service. The endpoint calls it once per new start/finish pair, then keeps the response in Django's file cache for 24 hours.
- **OpenStreetMap Nominatim** is used only when an input is an address instead of coordinates. It is also used by a separate, one-time data-preparation command; it is never called to choose stops during a request.
- The supplied CSV is in `data/` and is loaded into SQLite, so price lookup is local and fast.
- Route geometry is returned as standard GeoJSON. This is map data, ready for Leaflet, Mapbox, or Google Maps to draw, without committing to a paid map provider.

## Set up

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py import_fuel_prices
```

The CSV does not include latitude/longitude. Run this one-time preparation job before a full demo:

```powershell
# Quick demo preparation; run again with a larger limit or no --limit for all stations.
python manage.py geocode_fuel_stations --limit 100
```

Nominatim's public service permits roughly one request per second, so fully geocoding 8,151 records takes time. That trade-off is intentional: it keeps the user-facing API fast and avoids any geocoding during its normal request path. For production, I would obtain licensed coordinates or run this job asynchronously with a dedicated geocoder.

Start the server:

```powershell
python manage.py runserver
```

## Call the API

`POST http://127.0.0.1:8000/api/v1/route-plan/`

Use raw JSON in Postman:

```json
{
  "start": {"latitude": 41.8781, "longitude": -87.6298},
  "finish": {"latitude": 39.7392, "longitude": -104.9903}
}
```

Addresses are also accepted, which adds at most two cached Nominatim lookups:

```json
{"start": "Chicago, IL", "finish": "Denver, CO"}
```

The result contains:

- `route.geometry` — a GeoJSON `LineString` for a map.
- `fuel_stops` — selected station, price, coordinates, route mile marker, detour, gallons, and estimated cost.
- `total_money_spent_on_fuel` — cost of refills during the trip at 10 MPG. The model assumes a full tank at departure, which is stated in `vehicle`.

## Fuel-stop algorithm

For stations within 12 miles of the route, the planner projects each station onto the route. Whenever the remaining leg would exceed 500 miles, it chooses the lowest-price reachable station roughly 300–480 miles after the last fill (price first, detour as tie-breaker). The 20-mile buffer leaves room for the station detour. This is a clear greedy baseline rather than a claim of globally perfect optimisation.

## Tests and quality checks

```powershell
python manage.py check
python manage.py test
```

## Five-minute Loom outline

1. Show this README and say the application uses one cached OSRM route request.
2. Run `migrate`, `import_fuel_prices`, and explain that station coordinates are prepared outside requests.
3. Start Django, show Postman configured with the POST URL and JSON above.
4. Send the request, point out `distance_miles`, GeoJSON route, stops, per-stop price, and total cost.
5. Open `route_fuel/services.py`: explain the cache, 500-mile constraint, and lowest-price choice.
6. Close by mentioning the production improvement: PostgreSQL/PostGIS for faster geographic filtering and a scheduled price/coordinate importer.

## Sensible production next steps

Move from SQLite to PostgreSQL/PostGIS, use a spatial index rather than scanning stations in Python, protect API keys/secrets with environment variables, add rate limiting and structured logs, and use a commercial routing/geocoding provider with an SLA if this becomes customer-facing.
