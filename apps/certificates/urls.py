from django.urls import path

from . import views

app_name = "certificates"

urlpatterns = [
    path("verify/<uuid:verification_slug>/", views.verify, name="verify"),
    path("certificates/<str:serial>/", views.my_certificate, name="mine"),
]
