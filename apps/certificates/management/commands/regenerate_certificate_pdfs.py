from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from apps.certificates.models import Certificate
from apps.certificates.pdf import build_certificate_pdf


class Command(BaseCommand):
    help = (
        "Rebuilds and re-saves the PDF for one certificate (--serial) or "
        "every certificate (--all), using whatever storage backend is "
        "currently active. Needed after: (1) a PDF design change, or "
        "(2) switching storage backends — a certificate issued before "
        "file storage was wired to Supabase was saved to local disk, "
        "which 404s in production; re-running this after the storage "
        "env vars are set pushes a fresh copy to the real backend."
    )

    def add_arguments(self, parser):
        parser.add_argument("--serial", help="Regenerate just this one certificate's serial.")
        parser.add_argument("--all", action="store_true", help="Regenerate every certificate.")

    def handle(self, *args, **options):
        if options["serial"]:
            certificates = Certificate.objects.filter(serial=options["serial"])
            if not certificates.exists():
                self.stderr.write(self.style.ERROR(f"No certificate with serial {options['serial']!r}."))
                return
        elif options["all"]:
            certificates = Certificate.objects.all()
        else:
            self.stderr.write(self.style.ERROR("Pass --serial <serial> or --all."))
            return

        count = 0
        for certificate in certificates:
            pdf_bytes = build_certificate_pdf(certificate)
            certificate.pdf.save(f"{certificate.serial}.pdf", ContentFile(pdf_bytes), save=True)
            count += 1
            self.stdout.write(self.style.SUCCESS(f"Regenerated: {certificate.serial}"))

        self.stdout.write(self.style.SUCCESS(f"Done — {count} certificate(s) regenerated."))
