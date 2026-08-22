from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render

from .models import Certificate


def verify(request, verification_slug):
    """Public, no auth — build spec §4: "Shows: name, course, issue
    date, serial, status. Nothing else." A missing or revoked
    certificate must return a clear negative state, not a 404 that
    looks like a broken link and not a 500."""
    certificate = Certificate.objects.filter(verification_slug=verification_slug).first()
    return render(request, "certificates/verify.html", {"certificate": certificate})


@login_required
def my_certificate(request, serial):
    certificate = get_object_or_404(Certificate, serial=serial, enrollment__user=request.user)
    return render(request, "certificates/mine.html", {"certificate": certificate})
