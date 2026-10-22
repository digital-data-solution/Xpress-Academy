from django import forms


class LeadCaptureForm(forms.Form):
    email = forms.EmailField()


class SelarActivationForm(forms.Form):
    name = forms.CharField(max_length=200)
    email = forms.EmailField()
    reference = forms.CharField(max_length=40)
