from django.urls import path
from route_fuel.views import route_plan

urlpatterns = [path("api/v1/route-plan/", route_plan, name="route-plan")]
