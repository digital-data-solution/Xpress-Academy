from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse
from django.urls import include, path

from apps.catalog.sitemaps import CourseSitemap


def health_check(request):
    """Used by Render's health check probe (Phase 9). Deliberately does
    not touch the database — this proves the process is up, not that
    every dependency is healthy."""
    return HttpResponse("ok")


def robots_txt(request):
    lines = ["User-agent: *", "Allow: /", f"Sitemap: {settings.SITE_URL}/sitemap.xml"]
    return HttpResponse("\n".join(lines), content_type="text/plain")


sitemaps = {"courses": CourseSitemap}

urlpatterns = [
    path(settings.ADMIN_URL_PATH, admin.site.urls),
    path("healthz/", health_check, name="health-check"),
    path("robots.txt", robots_txt, name="robots"),
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="sitemap"),
    # django-ckeditor-5's widget always calls reverse() for this name
    # when rendering, even though our toolbar doesn't expose the
    # upload button — the URL must exist or every rich-text field
    # 500s on render. The view itself checks staff permission.
    path("ckeditor5/", include("django_ckeditor_5.urls")),
    path("account/", include("apps.accounts.urls")),
    path("", include("apps.enrollment.urls")),
    path("", include("apps.assessment.urls")),
    path("", include("apps.certificates.urls")),
    path("", include("apps.payments.urls")),
    path("", include("apps.operations.urls")),
    path("", include("apps.instructors.urls")),
    # catalog owns "/" (landing) and "/courses/..." — included last so
    # its catch-all-shaped slug pattern never shadows a more specific
    # path above it.
    path("", include("apps.catalog.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
