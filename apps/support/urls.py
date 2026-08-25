from django.urls import path

from . import views

app_name = "support"

urlpatterns = [
    path("support/", views.inbox, name="inbox"),
    path("support/<int:ticket_id>/", views.thread, name="thread"),
]
