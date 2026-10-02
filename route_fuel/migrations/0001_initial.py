# Generated manually for this small assessment project.
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="FuelStation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("opis_id", models.CharField(max_length=30)), ("name", models.CharField(max_length=255)),
                ("address", models.CharField(max_length=300)), ("city", models.CharField(max_length=120)),
                ("state", models.CharField(max_length=2)), ("price_per_gallon", models.DecimalField(decimal_places=4, max_digits=7)),
                ("latitude", models.FloatField(blank=True, null=True)), ("longitude", models.FloatField(blank=True, null=True)),
            ],
        ),
        migrations.AddIndex(model_name="fuelstation", index=models.Index(fields=["latitude", "longitude"], name="route_fuel_latitud_5062fa_idx")),
        migrations.AddIndex(model_name="fuelstation", index=models.Index(fields=["state"], name="route_fuel_state_a69c0f_idx")),
    ]
