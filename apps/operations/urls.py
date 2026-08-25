from django.urls import path

from . import views

app_name = "operations"

urlpatterns = [
    path("ops/", views.ops_queue, name="queue"),
    path("ops/growth/", views.growth, name="growth"),
    path("ops/<int:signal_id>/act/", views.ops_act, name="act"),
]
