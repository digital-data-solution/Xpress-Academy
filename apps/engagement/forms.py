from django import forms


class LeadCaptureForm(forms.Form):
    email = forms.EmailField()
