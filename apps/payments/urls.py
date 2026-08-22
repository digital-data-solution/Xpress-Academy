from django.urls import path

from . import views

app_name = "payments"

urlpatterns = [
    path("checkout/return/", views.checkout_return, name="checkout_return"),
    path("checkout/<slug:course_slug>/", views.checkout, name="checkout"),
]
