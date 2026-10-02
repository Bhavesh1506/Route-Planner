import csv
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from route_fuel.models import FuelStation


class Command(BaseCommand):
    help = "Import the supplied OPIS fuel-price CSV into SQLite."

    def add_arguments(self, parser):
        parser.add_argument("--file", default="data/fuel-prices-for-be-assessment.csv")

    def handle(self, *args, **options):
        filename = Path(options["file"])
        if not filename.exists():
            raise CommandError(f"CSV not found: {filename}")
        FuelStation.objects.all().delete()
        batch = []
        with filename.open(encoding="utf-8-sig", newline="") as csv_file:
            for row in csv.DictReader(csv_file):
                try:
                    batch.append(FuelStation(
                        opis_id=row["OPIS Truckstop ID"], name=row["Truckstop Name"], address=row["Address"],
                        city=row["City"], state=row["State"], price_per_gallon=Decimal(row["Retail Price"]),
                    ))
                except (KeyError, ValueError):
                    continue
                if len(batch) == 500:
                    FuelStation.objects.bulk_create(batch)
                    batch = []
        FuelStation.objects.bulk_create(batch)
        self.stdout.write(self.style.SUCCESS(f"Imported {FuelStation.objects.count()} fuel price records."))
