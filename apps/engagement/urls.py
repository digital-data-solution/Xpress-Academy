from django.urls import path

from . import views

app_name = "engagement"

urlpatterns = [
    path("internal/run-scheduled-tasks/", views.run_scheduled_tasks, name="run_scheduled_tasks"),
    path("leads/capture/", views.capture_lead, name="capture_lead"),
]
