from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import User


class SignupForm(forms.Form):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    marketing_opt_in = forms.BooleanField(required=False, initial=False)

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError("An account with this email already exists.")
        return email

    def clean_password(self):
        password = self.cleaned_data["password"]
        validate_password(password)  # uses AUTH_PASSWORD_VALIDATORS, not a hand-rolled rule
        return password

    def save(self):
        user = User.objects.create_user(
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password"],
            first_name=self.cleaned_data["first_name"],
            last_name=self.cleaned_data.get("last_name", ""),
        )
        # The post_save signal (signal_receivers.py) already created a
        # Profile row for this user — update it rather than creating a
        # second one, which would violate the OneToOne constraint.
        user.profile.marketing_opt_in = self.cleaned_data.get("marketing_opt_in", False)
        user.profile.save(update_fields=["marketing_opt_in"])
        return user


class ForgotPasswordForm(forms.Form):
    email = forms.EmailField()

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()
