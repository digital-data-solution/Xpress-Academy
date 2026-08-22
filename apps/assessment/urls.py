from django.urls import path

from . import views

app_name = "assessment"

urlpatterns = [
    path("learn/<slug:course_slug>/quiz/<int:quiz_id>/", views.quiz_intro, name="quiz_intro"),
    path("learn/<slug:course_slug>/quiz/<int:quiz_id>/attempt/<int:attempt_id>/", views.attempt_view, name="attempt"),
    path(
        "learn/<slug:course_slug>/quiz/<int:quiz_id>/attempt/<int:attempt_id>/answer/",
        views.save_answer_ajax,
        name="save_answer",
    ),
    path(
        "learn/<slug:course_slug>/quiz/<int:quiz_id>/attempt/<int:attempt_id>/results/",
        views.results_view,
        name="results",
    ),
]
