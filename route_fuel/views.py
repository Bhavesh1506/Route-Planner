import json

import requests
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .services import choose_fuel_plan, get_route, resolve_location, stations_near_route


@require_POST
def route_plan(request):
    """POST start and finish, returning GeoJSON a client can draw directly on a map."""
    try:
        body = json.loads(request.body)
        start = resolve_location(body.get("start"))
        finish = resolve_location(body.get("finish"))
        route = get_route(start[:2], finish[:2])
        line = route["geometry"]["coordinates"]
        stations = stations_near_route(line)
        stops, fuel_cost = choose_fuel_plan(route["distance"] / 1609.344, stations)
        map_features = [{"type": "Feature", "geometry": route["geometry"], "properties": {"kind": "route"}}]
        map_features.extend({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [stop["longitude"], stop["latitude"]]},
            "properties": {"kind": "fuel_stop", "name": stop["name"], "price_per_gallon": stop["price"]},
        } for stop in stops)
        return JsonResponse({
            "start": {"display_name": start[2], "longitude": start[0], "latitude": start[1]},
            "finish": {"display_name": finish[2], "longitude": finish[0], "latitude": finish[1]},
            "route": {"distance_miles": round(route["distance"] / 1609.344, 1), "duration_minutes": round(route["duration"] / 60, 1), "geometry": route["geometry"]},
            "vehicle": {"mpg": 10, "maximum_range_miles": 500, "starts_with_full_tank": True},
            "fuel_stops": stops,
            "total_money_spent_on_fuel": fuel_cost,
            "map": {"type": "FeatureCollection", "features": map_features},
            "notes": ["Route is fetched once from OSRM and cached for 24 hours.", "Fuel prices are from the supplied CSV; stops require station coordinates imported with geocode_fuel_stations."],
        })
    except (ValueError, TypeError, json.JSONDecodeError) as error:
        return JsonResponse({"error": str(error)}, status=400)
    except requests.RequestException:
        return JsonResponse({"error": "Routing/geocoding provider is temporarily unavailable."}, status=503)
