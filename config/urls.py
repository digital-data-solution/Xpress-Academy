from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path


def health_check(request):
    """Used by Render's health check probe (Phase 9). Deliberately does
    not touch the database — this proves the process is up, not that
    every dependency is healthy."""
    return HttpResponse("ok")


urlpatterns = [
    path(settings.ADMIN_URL_PATH, admin.site.urls),
    path("healthz/", health_check, name="health-check"),
    # django-ckeditor-5's widget always calls reverse() for this name
    # when rendering, even though our toolbar doesn't expose the
    # upload button — the URL must exist or every rich-text field
    # 500s on render. The view itself checks staff permission.
    path("ckeditor5/", include("django_ckeditor_5.urls")),
    path("account/", include("apps.accounts.urls")),
    path("", include("apps.enrollment.urls")),
    path("", include("apps.assessment.urls")),
    path("", include("apps.certificates.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
