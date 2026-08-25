from django import forms

from .models import Instructor


class InstructorApplicationForm(forms.ModelForm):
    class Meta:
        model = Instructor
        fields = ["display_name", "headline", "bio", "credentials"]


class CourseMetadataForm(forms.ModelForm):
    """Instructor-facing course editing — metadata only. Full module/
    lesson/quiz authoring stays in Django admin (staff-managed), same
    as every other course on the platform; this is deliberately small."""

    class Meta:
        from apps.catalog.models import Course
        model = Course
        fields = [
            "title", "subtitle", "description",
            "pricing_model", "price_ngn", "minimum_price_ngn",
            "audience", "level",
        ]
