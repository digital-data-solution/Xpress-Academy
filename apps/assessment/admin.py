from django import forms
from django.contrib import admin, messages
from django.shortcuts import redirect, render
from django.urls import path, reverse

from .csv_import import import_questions_from_csv
from .models import Attempt, AttemptAnswer, Choice, Question, QuestionBank, Quiz, Topic


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "question_count"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}

    def question_count(self, obj):
        return obj.questions.count()

    question_count.short_description = "Questions"


class CSVImportForm(forms.Form):
    csv_file = forms.FileField(label="CSV file")


@admin.register(QuestionBank)
class QuestionBankAdmin(admin.ModelAdmin):
    list_display = ["name", "organization", "question_count", "well_formed_count"]
    list_filter = ["organization"]
    search_fields = ["name"]
    change_form_template = "admin/assessment/questionbank/change_form.html"

    def question_count(self, obj):
        return obj.questions.count()

    def well_formed_count(self, obj):
        total = obj.questions.count()
        well_formed = sum(1 for q in obj.questions.all() if q.is_well_formed)
        return f"{well_formed} / {total} ready"

    well_formed_count.short_description = "Ready for quizzes"

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "<int:bank_id>/import-csv/",
                self.admin_site.admin_view(self.import_csv_view),
                name="assessment_questionbank_import_csv",
            ),
        ]
        return custom + urls

    def import_csv_view(self, request, bank_id):
        bank = self.get_object(request, bank_id)
        if bank is None:
            messages.error(request, "Question bank not found.")
            return redirect("admin:assessment_questionbank_changelist")

        if request.method == "POST":
            form = CSVImportForm(request.POST, request.FILES)
            if form.is_valid():
                result = import_questions_from_csv(bank, form.cleaned_data["csv_file"])
                if result.created:
                    messages.success(request, f"Imported {result.created} question(s) into {bank.name}.")
                for err in result.errors[:20]:
                    messages.warning(request, err)
                if len(result.errors) > 20:
                    messages.warning(request, f"...and {len(result.errors) - 20} more row(s) with problems.")
                return redirect("admin:assessment_questionbank_change", bank_id)
        else:
            form = CSVImportForm()

        return render(
            request,
            "admin/assessment/questionbank/import_csv.html",
            {
                "form": form,
                "bank": bank,
                "opts": self.model._meta,
                "title": f"Import questions — {bank.name}",
            },
        )


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4
    fields = ["order", "text", "is_correct"]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ["stem_short", "bank", "type", "difficulty", "is_active", "well_formed_display"]
    list_filter = ["bank", "type", "difficulty", "is_active", "topics"]
    search_fields = ["stem", "explanation"]
    filter_horizontal = ["topics"]
    inlines = [ChoiceInline]

    def stem_short(self, obj):
        return obj.stem[:80]

    stem_short.short_description = "Stem"

    def well_formed_display(self, obj):
        return obj.is_well_formed

    well_formed_display.short_description = "Ready"
    well_formed_display.boolean = True


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ["title", "scope", "module", "course", "bank", "question_count", "pass_mark", "max_attempts"]
    list_filter = ["scope", "bank"]
    search_fields = ["title"]
    filter_horizontal = ["topic_filter"]


class AttemptAnswerInline(admin.TabularInline):
    model = AttemptAnswer
    extra = 0
    fields = ["question", "is_correct"]
    readonly_fields = ["question", "is_correct"]
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Attempt)
class AttemptAdmin(admin.ModelAdmin):
    list_display = ["enrollment", "quiz", "attempt_number", "score_percent", "passed", "started_at", "submitted_at"]
    list_filter = ["quiz", "passed"]
    search_fields = ["enrollment__user__email", "quiz__title"]
    readonly_fields = ["enrollment", "quiz", "attempt_number", "started_at", "submitted_at",
                        "expires_at", "score_percent", "passed", "question_snapshot"]
    inlines = [AttemptAnswerInline]

    def has_add_permission(self, request):
        # Attempts are created by the learner starting a quiz, not authored in admin.
        return False
