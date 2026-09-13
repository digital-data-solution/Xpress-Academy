from django.urls import path

from . import views

app_name = "quizbuilder"

urlpatterns = [
    path("quizzes/", views.my_quizzes, name="my_quizzes"),
    path("quizzes/new/", views.quiz_create, name="quiz_create"),
    path("quizzes/<slug:slug>/created/", views.quiz_created, name="quiz_created"),
    path("quizzes/<slug:slug>/edit/", views.quiz_edit, name="quiz_edit"),
    path("quizzes/<slug:slug>/toggle/", views.quiz_toggle_active, name="quiz_toggle_active"),
    path("quizzes/<slug:slug>/delete/", views.quiz_delete, name="quiz_delete"),
    path("quizzes/<slug:slug>/duplicate/", views.quiz_duplicate, name="quiz_duplicate"),
    path("quizzes/<slug:slug>/responses/", views.quiz_responses, name="quiz_responses"),
    path("quizzes/<slug:slug>/responses/export.csv", views.quiz_export_csv, name="quiz_export_csv"),
    path("quizzes/<slug:slug>/responses/<uuid:response_uuid>/delete/", views.response_delete, name="response_delete"),
    path("sessions/", views.session_list, name="session_list"),
    path("sessions/new/", views.session_create, name="session_create"),
    path("sessions/<int:pk>/", views.session_report, name="session_report"),
    path("sessions/<int:pk>/export.csv", views.session_export_csv, name="session_export_csv"),
    # Short public path, deliberately not under /quizzes/ — this is
    # the link that actually gets shared with respondents.
    path("q/<slug:slug>/", views.quiz_take, name="quiz_take"),
    path("q/<slug:slug>/r/<uuid:response_uuid>/", views.quiz_result, name="quiz_result"),
]
