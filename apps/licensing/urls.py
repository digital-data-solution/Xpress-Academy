from django.urls import path

from . import views

app_name = "licensing"

urlpatterns = [
    path("school/<slug:institution_slug>/", views.school_dashboard, name="school_dashboard"),
    path("diagnostic/<slug:test_slug>/", views.diagnostic_intro, name="diagnostic_intro"),
    path(
        "diagnostic/<slug:test_slug>/attempt/<uuid:attempt_uuid>/",
        views.diagnostic_attempt_view,
        name="diagnostic_attempt",
    ),
    path(
        "diagnostic/<slug:test_slug>/attempt/<uuid:attempt_uuid>/answer/",
        views.diagnostic_save_answer_ajax,
        name="diagnostic_save_answer",
    ),
    path(
        "diagnostic/<slug:test_slug>/attempt/<uuid:attempt_uuid>/results/",
        views.diagnostic_results_view,
        name="diagnostic_results",
    ),
]
