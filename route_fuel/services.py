"""Small, dependency-light helpers for routing and choosing fuel stops."""
from __future__ import annotations

from math import cos, radians, sqrt
from typing import Any

import requests
from django.core.cache import cache

from .models import FuelStation

OSRM_URL = "https://router.project-osrm.org/route/v1/driving"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
MILES_PER_DEGREE = 69.0


def miles_between(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Fast enough approximation for the short route segments OSRM returns."""
    lat_scale = MILES_PER_DEGREE
    lon_scale = MILES_PER_DEGREE * cos(radians((a[1] + b[1]) / 2))
    return sqrt(((a[0] - b[0]) * lon_scale) ** 2 + ((a[1] - b[1]) * lat_scale) ** 2)


def resolve_location(value: Any) -> tuple[float, float, str]:
    """Accept {latitude, longitude}, or a US address/city string."""
    if isinstance(value, dict) and {"latitude", "longitude"} <= value.keys():
        longitude, latitude = float(value["longitude"]), float(value["latitude"])
        # Broad continental/Alaska/Hawaii bounds; strings are verified by Nominatim.
        if not (15 <= latitude <= 72 and -180 <= longitude <= -60):
            raise ValueError("Both locations must be within the USA.")
        return longitude, latitude, "coordinates supplied by caller"
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Use an address string or {latitude, longitude}.")
    key = f"geocode:{value.strip().lower()}"
    saved = cache.get(key)
    if saved:
        return tuple(saved)
    response = requests.get(
        NOMINATIM_URL,
        params={"q": value, "format": "jsonv2", "limit": 1, "addressdetails": 1, "countrycodes": "us"},
        headers={"User-Agent": "route-fuel-assessment/1.0"},
        timeout=8,
    )
    response.raise_for_status()
    rows = response.json()
    if not rows or rows[0].get("address", {}).get("country_code") != "us":
        raise ValueError("Location was not found in the USA.")
    result = (float(rows[0]["lon"]), float(rows[0]["lat"]), rows[0]["display_name"])
    cache.set(key, result, 60 * 60 * 24 * 30)
    return result


def get_route(start: tuple[float, float], finish: tuple[float, float]) -> dict[str, Any]:
    """Exactly one OSRM routing request; identical requests are cached for 24 hours."""
    key = f"route:{start[0]:.4f},{start[1]:.4f}:{finish[0]:.4f},{finish[1]:.4f}"
    cached = cache.get(key)
    if cached:
        return cached
    response = requests.get(
        f"{OSRM_URL}/{start[0]},{start[1]};{finish[0]},{finish[1]}",
        params={"overview": "full", "geometries": "geojson", "steps": "false"},
        timeout=12,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("code") != "Ok" or not data.get("routes"):
        raise ValueError("No drivable route was found.")
    route = data["routes"][0]
    cache.set(key, route, 60 * 60 * 24)
    return route


def _project_on_route(point: tuple[float, float], line: list[list[float]]) -> tuple[float, float]:
    """Return (mile marker, distance from route) using a local flat projection."""
    total = 0.0
    best_distance, best_marker = float("inf"), 0.0
    for start, end in zip(line, line[1:]):
        segment = miles_between(tuple(start), tuple(end))
        mid_lat = (start[1] + end[1]) / 2
        scale_x = MILES_PER_DEGREE * cos(radians(mid_lat))
        scale_y = MILES_PER_DEGREE
        vx, vy = (end[0] - start[0]) * scale_x, (end[1] - start[1]) * scale_y
        wx, wy = (point[0] - start[0]) * scale_x, (point[1] - start[1]) * scale_y
        fraction = max(0.0, min(1.0, (wx * vx + wy * vy) / (vx * vx + vy * vy or 1)))
        distance = sqrt((wx - fraction * vx) ** 2 + (wy - fraction * vy) ** 2)
        if distance < best_distance:
            best_distance, best_marker = distance, total + fraction * segment
        total += segment
    return best_marker, best_distance


def stations_near_route(line: list[list[float]], corridor_miles: float = 12) -> list[dict[str, Any]]:
    stations = []
    for station in FuelStation.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True).iterator():
        mile, detour = _project_on_route((station.longitude, station.latitude), line)
        if detour <= corridor_miles:
            stations.append({
                "id": station.id, "name": station.name, "address": f"{station.address}, {station.city}, {station.state}",
                "price": float(station.price_per_gallon), "longitude": station.longitude, "latitude": station.latitude,
                "mile": mile, "detour": detour,
            })
    return sorted(stations, key=lambda item: item["mile"])


def choose_fuel_plan(total_miles: float, stations: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], float]:
    """Greedy choice: among reachable stations, prefer the cheapest one near tank range.

    The vehicle starts full. Each stop is chosen 300-480 miles after the last fill,
    keeping a safety buffer below the required 500-mile maximum range.
    """
    stops: list[dict[str, Any]] = []
    current = 0.0
    while total_miles - current > 500:
        reachable = [s for s in stations if current + 300 <= s["mile"] <= min(current + 480, total_miles - 20)]
        if not reachable:
            reachable = [s for s in stations if current + 50 <= s["mile"] <= current + 500]
        if not reachable:
            raise ValueError("No geocoded fuel station is available within 500 miles of the current leg.")
        # Price matters most; a shorter detour breaks ties.
        chosen = min(reachable, key=lambda s: (s["price"], s["detour"]))
        stops.append(chosen)
        current = chosen["mile"]

    # Cost is fuel consumed after departure. Starting with a full tank means a trip
    # below 500 miles has no refuelling purchase. Each stop is filled for remaining trip.
    total_cost = 0.0
    for index, stop in enumerate(stops):
        next_mile = stops[index + 1]["mile"] if index + 1 < len(stops) else total_miles
        gallons = (next_mile - stop["mile"]) / 10
        stop["gallons_to_buy"] = round(gallons, 2)
        stop["estimated_cost"] = round(gallons * stop["price"], 2)
        total_cost += gallons * stop["price"]
    return stops, round(total_cost, 2)
