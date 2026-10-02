from django.db import models


class FuelStation(models.Model):
    opis_id = models.CharField(max_length=30)
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=300)
    city = models.CharField(max_length=120)
    state = models.CharField(max_length=2)
    price_per_gallon = models.DecimalField(max_digits=7, decimal_places=4)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["latitude", "longitude"]), models.Index(fields=["state"])]
