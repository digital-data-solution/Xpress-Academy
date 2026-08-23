from django.urls import path

from . import views

app_name = "catalog"

urlpatterns = [
    path("", views.landing, name="landing"),
    path("courses/", views.course_catalog, name="course_catalog"),
    path("courses/<slug:slug>/", views.course_detail, name="course_detail"),
]
