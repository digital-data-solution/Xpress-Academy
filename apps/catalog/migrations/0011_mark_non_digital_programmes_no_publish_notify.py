# Data migration — the user's explicit request: the course-publish
# webhook (and whatever campaign system it feeds downstream) is meant
# for the "digital line" (Digital Skills, AI Skills, Business &
# Entrepreneurship) — their imported leads are interested in digital/
# data technology, business, and automation, not veterinary/breeding
# topics. Rather than hardcoding a slug allowlist in Python, this
# flips the explicit, admin-editable Programme.notify_on_publish flag
# on the two non-digital Programmes that exist today. Idempotent
# (plain .update(), safe to re-run) and reversible.

from django.db import migrations

NON_DIGITAL_PROGRAMME_SLUGS = ["dog-breeding", "veterinary-continuing-education"]


def mark_non_digital(apps, schema_editor):
    Programme = apps.get_model("catalog", "Programme")
    Programme.objects.filter(slug__in=NON_DIGITAL_PROGRAMME_SLUGS).update(notify_on_publish=False)


def reverse(apps, schema_editor):
    Programme = apps.get_model("catalog", "Programme")
    Programme.objects.filter(slug__in=NON_DIGITAL_PROGRAMME_SLUGS).update(notify_on_publish=True)


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0010_programme_notify_on_publish'),
    ]

    operations = [
        migrations.RunPython(mark_non_digital, reverse),
    ]
