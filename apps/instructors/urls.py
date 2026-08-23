from django.urls import path

from . import views

app_name = "instructors"

urlpatterns = [
    path("teach/apply/", views.apply, name="apply"),
    path("teach/dashboard/", views.dashboard, name="dashboard"),
    path("teach/courses/", views.course_list, name="course_list"),
    path("teach/courses/<slug:slug>/edit/", views.course_edit, name="course_edit"),
    path("teach/courses/<slug:slug>/submit/", views.course_submit, name="course_submit"),
    path("teach/courses/<slug:slug>/learners/", views.course_learners, name="course_learners"),
    path("teach/earnings/", views.earnings, name="earnings"),
    path("teach/marketing/", views.marketing, name="marketing"),
]
