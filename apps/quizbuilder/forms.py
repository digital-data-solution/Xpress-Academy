"""Question authoring deliberately uses a flat 4-option form
(option_a..option_d + correct_option), not a nested Question+Choice
formset — Django formsets don't nest cleanly, and every quiz on this
platform (exam-bank engine included) already treats "up to 4 lettered
options, one correct" as the standard MCQ shape. option_c/option_d
are optional so a true/false-style 2-option question works too."""
from django import forms
from django.forms import formset_factory

from .models import Quiz

OPTION_LETTERS = ["a", "b", "c", "d"]


class QuizForm(forms.ModelForm):
    class Meta:
        model = Quiz
        fields = ["title", "description", "time_limit_minutes", "show_score_immediately"]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "e.g. Fire Safety Training — Pre-Test"}),
            "description": forms.Textarea(attrs={"rows": 2, "placeholder": "Shown to respondents before they start (optional)."}),
        }


class QuestionForm(forms.Form):
    stem = forms.CharField(widget=forms.Textarea(attrs={"rows": 2, "placeholder": "Question text"}))
    option_a = forms.CharField(max_length=500, label="Option A")
    option_b = forms.CharField(max_length=500, label="Option B")
    option_c = forms.CharField(max_length=500, label="Option C", required=False)
    option_d = forms.CharField(max_length=500, label="Option D", required=False)
    correct_option = forms.ChoiceField(
        choices=[("a", "A"), ("b", "B"), ("c", "C"), ("d", "D")], widget=forms.RadioSelect
    )

    def clean(self):
        cleaned = super().clean()
        correct = cleaned.get("correct_option")
        if correct and not cleaned.get(f"option_{correct}"):
            self.add_error("correct_option", "The option you marked correct can't be left empty.")
        return cleaned

    def options(self):
        """(letter, field_name) pairs actually filled in — used by the
        template to render only as many option rows as exist, and by
        the view to build Choice rows."""
        return [(letter, f"option_{letter}") for letter in OPTION_LETTERS]


QuestionFormSet = formset_factory(QuestionForm, extra=1, min_num=1, validate_min=True, can_delete=True)


class RespondentForm(forms.Form):
    respondent_name = forms.CharField(max_length=255, label="Your name")
    respondent_email = forms.EmailField(label="Your email")
