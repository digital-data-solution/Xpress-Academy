from django.urls import path

from . import views

app_name = "enrollment"

urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("learn/<slug:course_slug>/", views.curriculum, name="curriculum"),
    path("learn/<slug:course_slug>/<slug:lesson_slug>/", views.lesson_player, name="lesson"),
    path("learn/<slug:course_slug>/<slug:lesson_slug>/complete/", views.mark_complete, name="mark_complete"),
]
