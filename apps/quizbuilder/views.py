from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from . import services
from .forms import QuestionFormSet, QuizForm, RespondentForm
from .models import Quiz, Response, TrainingSession


@login_required
def my_quizzes(request):
    quizzes = Quiz.objects.filter(created_by=request.user)
    return render(request, "quizbuilder/my_quizzes.html", {"quizzes": quizzes})


@login_required
def quiz_create(request):
    if request.method == "POST":
        quiz_form = QuizForm(request.POST)
        formset = QuestionFormSet(request.POST, prefix="q")
        if quiz_form.is_valid() and formset.is_valid():
            quiz = services.create_quiz_with_questions(
                user=request.user, quiz_form=quiz_form, question_forms=formset
            )
            return redirect("quizbuilder:quiz_created", slug=quiz.slug)
    else:
        quiz_form = QuizForm()
        formset = QuestionFormSet(prefix="q")
    return render(request, "quizbuilder/quiz_form.html", {
        "quiz_form": quiz_form, "formset": formset, "is_edit": False,
    })


@login_required
def quiz_created(request, slug):
    """Landing page right after creation — surfaces the shareable link
    front and center, since that's the entire point of the tool."""
    quiz = get_object_or_404(Quiz, slug=slug, created_by=request.user)
    return render(request, "quizbuilder/quiz_created.html", {"quiz": quiz})


@login_required
def quiz_edit(request, slug):
    quiz = get_object_or_404(Quiz, slug=slug, created_by=request.user)
    if quiz.response_count:
        # Editing questions out from under existing graded responses
        # would silently corrupt their recorded answers/scores (see
        # the model's "No snapshotting" note) — block it outright
        # rather than build snapshot infrastructure for an MVP.
        # Title/description/settings can still change any time.
        editable_questions = False
    else:
        editable_questions = True

    initial = [
        services.question_to_formset_initial(q)
        for q in quiz.questions.prefetch_related("choices").all()
    ]

    if request.method == "POST":
        quiz_form = QuizForm(request.POST, instance=quiz)
        formset = QuestionFormSet(request.POST, prefix="q") if editable_questions else None
        forms_valid = quiz_form.is_valid() and (not editable_questions or formset.is_valid())
        if forms_valid:
            quiz_form.save()
            if editable_questions:
                services.replace_quiz_questions(quiz=quiz, question_forms=formset)
            return redirect("quizbuilder:my_quizzes")
    else:
        quiz_form = QuizForm(instance=quiz)
        formset = QuestionFormSet(prefix="q", initial=initial) if editable_questions else None
        if formset is not None:
            formset.extra = 0

    return render(request, "quizbuilder/quiz_form.html", {
        "quiz_form": quiz_form, "formset": formset, "is_edit": True, "quiz": quiz,
        "editable_questions": editable_questions,
    })


@login_required
def quiz_toggle_active(request, slug):
    quiz = get_object_or_404(Quiz, slug=slug, created_by=request.user)
    if request.method == "POST":
        quiz.is_active = not quiz.is_active
        quiz.save(update_fields=["is_active"])
    return redirect("quizbuilder:my_quizzes")


@login_required
def quiz_responses(request, slug):
    quiz = get_object_or_404(Quiz, slug=slug, created_by=request.user)
    rows = list(services.response_rows_for_export(quiz))
    return render(request, "quizbuilder/quiz_responses.html", {"quiz": quiz, "rows": rows})


@login_required
def quiz_export_csv(request, slug):
    quiz = get_object_or_404(Quiz, slug=slug, created_by=request.user)
    content = services.quiz_export_csv_content(quiz)
    resp = HttpResponse(content, content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="{quiz.slug}-responses.csv"'
    return resp


# --- Public, unauthenticated quiz-taking flow -----------------------

def _get_quiz(slug):
    return get_object_or_404(Quiz, slug=slug, is_active=True)


def quiz_take(request, slug):
    quiz = _get_quiz(slug)
    questions = list(quiz.questions.prefetch_related("choices"))
    if not questions:
        raise Http404("This quiz has no questions yet.")

    if request.method == "POST":
        respondent_form = RespondentForm(request.POST)
        if respondent_form.is_valid():
            response = Response.objects.create(
                quiz=quiz,
                respondent_name=respondent_form.cleaned_data["respondent_name"],
                respondent_email=respondent_form.cleaned_data["respondent_email"],
            )
            posted_answers = {
                str(q.id): request.POST.get(f"question_{q.id}") for q in questions
            }
            services.score_and_submit_response(response=response, posted_answers=posted_answers)
            return redirect("quizbuilder:quiz_result", slug=quiz.slug, response_uuid=response.uuid)
    else:
        respondent_form = RespondentForm()

    return render(request, "quizbuilder/quiz_take.html", {
        "quiz": quiz, "questions": questions, "respondent_form": respondent_form,
    })


def quiz_result(request, slug, response_uuid):
    quiz = _get_quiz(slug)
    response = get_object_or_404(Response, uuid=response_uuid, quiz=quiz)
    if not response.submitted_at:
        raise Http404("This response was never submitted.")

    rows = None
    if quiz.show_score_immediately:
        rows = []
        for q in quiz.questions.prefetch_related("choices"):
            chosen_id = response.answers.get(str(q.id))
            rows.append({
                "stem": q.stem,
                "choices": [
                    {"text": c.text, "is_correct": c.is_correct, "was_selected": str(c.id) == str(chosen_id)}
                    for c in q.choices.all()
                ],
            })

    return render(request, "quizbuilder/quiz_result.html", {"quiz": quiz, "response": response, "rows": rows})


# --- Training sessions (pre/post pairing) ----------------------------

@login_required
def session_list(request):
    sessions = TrainingSession.objects.filter(created_by=request.user)
    my_quizzes_qs = Quiz.objects.filter(created_by=request.user)
    return render(request, "quizbuilder/session_list.html", {"sessions": sessions, "quizzes": my_quizzes_qs})


@login_required
def session_create(request):
    quizzes = Quiz.objects.filter(created_by=request.user)
    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        pre_id = request.POST.get("pre_quiz")
        post_id = request.POST.get("post_quiz")
        if title:
            session = TrainingSession.objects.create(
                created_by=request.user,
                title=title,
                pre_quiz_id=pre_id or None,
                post_quiz_id=post_id or None,
            )
            return redirect("quizbuilder:session_report", pk=session.pk)
    return render(request, "quizbuilder/session_form.html", {"quizzes": quizzes})


@login_required
def session_report(request, pk):
    session = get_object_or_404(TrainingSession, pk=pk, created_by=request.user)
    rows = services.paired_session_rows(session)
    return render(request, "quizbuilder/session_report.html", {"session": session, "rows": rows})


@login_required
def session_export_csv(request, pk):
    session = get_object_or_404(TrainingSession, pk=pk, created_by=request.user)
    content = services.session_export_csv_content(session)
    resp = HttpResponse(content, content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="{session.title}-pre-post-report.csv"'
    return resp
