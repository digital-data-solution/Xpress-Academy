from django.contrib import admin

from .models import Choice, Question, Quiz, Response, TrainingSession


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 0


class QuestionInline(admin.TabularInline):
    model = Question
    extra = 0
    show_change_link = True


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ["title", "created_by", "is_active", "question_count", "response_count", "created_at"]
    list_filter = ["is_active"]
    search_fields = ["title", "slug", "created_by__email"]
    autocomplete_fields = ["created_by"]
    inlines = [QuestionInline]


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ["stem", "quiz", "order"]
    list_filter = ["quiz"]
    inlines = [ChoiceInline]


@admin.register(Response)
class ResponseAdmin(admin.ModelAdmin):
    list_display = ["respondent_name", "respondent_email", "quiz", "score_percent", "submitted_at"]
    list_filter = ["quiz"]
    search_fields = ["respondent_name", "respondent_email"]


@admin.register(TrainingSession)
class TrainingSessionAdmin(admin.ModelAdmin):
    list_display = ["title", "created_by", "pre_quiz", "post_quiz", "created_at"]
    autocomplete_fields = ["created_by", "pre_quiz", "post_quiz"]
