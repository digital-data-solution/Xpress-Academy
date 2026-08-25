from django import forms


class NewTicketForm(forms.Form):
    subject = forms.CharField(max_length=255)
    body = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}))


class ReplyForm(forms.Form):
    body = forms.CharField(widget=forms.Textarea(attrs={"rows": 3}))
