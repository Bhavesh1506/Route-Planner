from django.test import TestCase

from .services import choose_fuel_plan, miles_between


class FuelPlanningTests(TestCase):
    def test_short_trip_needs_no_refill_when_starting_full(self):
        stops, cost = choose_fuel_plan(450, [])
        self.assertEqual(stops, [])
        self.assertEqual(cost, 0)

    def test_cheapest_reachable_stop_is_selected(self):
        stations = [
            {"name": "Expensive", "mile": 400, "price": 4.2, "detour": 1},
            {"name": "Affordable", "mile": 420, "price": 3.0, "detour": 2},
        ]
        stops, cost = choose_fuel_plan(800, stations)
        self.assertEqual(stops[0]["name"], "Affordable")
        self.assertAlmostEqual(cost, (800 - 420) / 10 * 3.0)

    def test_distance_helper(self):
        self.assertAlmostEqual(miles_between((0, 0), (0, 1)), 69, delta=1)
