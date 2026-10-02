"""One-time station preparation command; never called by the route endpoint."""
import time

import requests
from django.core.management.base import BaseCommand

from route_fuel.models import FuelStation
from route_fuel.services import NOMINATIM_URL


class Command(BaseCommand):
    help = "Add coordinates to imported fuel stations using OpenStreetMap Nominatim (slow, one-time task)."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=None, help="Useful for a quick demo import.")

    def handle(self, *args, **options):
        stations = FuelStation.objects.filter(latitude__isnull=True).order_by("id")
        if options["limit"]:
            stations = stations[:options["limit"]]
        updated = 0
        for station in stations.iterator():
            query = f"{station.address}, {station.city}, {station.state}, USA"
            try:
                response = requests.get(NOMINATIM_URL, params={"q": query, "format": "jsonv2", "limit": 1, "countrycodes": "us"}, headers={"User-Agent": "route-fuel-assessment/1.0"}, timeout=12)
                row = response.json()[0]
                station.latitude, station.longitude = float(row["lat"]), float(row["lon"])
                station.save(update_fields=["latitude", "longitude"])
                updated += 1
            except (requests.RequestException, IndexError, KeyError, ValueError):
                self.stderr.write(f"Could not locate: {query}")
            # Nominatim's public policy asks for no more than one request/second.
            time.sleep(1.1)
        self.stdout.write(self.style.SUCCESS(f"Geocoded {updated} station records."))
