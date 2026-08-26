# Data migration — supersedes 0011's binary notify_on_publish split
# now that there are two real destinations (DIGITAL and VET) instead
# of just one. Sets the explicit line per existing Programme: the
# three digital-line Programmes get DIGITAL (same set that had
# notify_on_publish=True), the two veterinary-line Programmes get VET
# (previously notify_on_publish=False, now pointed at the new Xpress
# Vet Marketplace destination instead of just being off). Idempotent
# (.update() calls) and reversible.

from django.db import migrations

DIGITAL_PROGRAMME_SLUGS = ["digital-skills", "ai-skills", "business-and-entrepreneurship"]
VET_PROGRAMME_SLUGS = ["dog-breeding", "veterinary-continuing-education"]


def set_lines(apps, schema_editor):
    Programme = apps.get_model("catalog", "Programme")
    Programme.objects.filter(slug__in=DIGITAL_PROGRAMME_SLUGS).update(webhook_line="DIGITAL")
    Programme.objects.filter(slug__in=VET_PROGRAMME_SLUGS).update(webhook_line="VET")


def reverse(apps, schema_editor):
    Programme = apps.get_model("catalog", "Programme")
    Programme.objects.filter(
        slug__in=DIGITAL_PROGRAMME_SLUGS + VET_PROGRAMME_SLUGS
    ).update(webhook_line="NONE")


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0012_remove_programme_notify_on_publish_and_more'),
    ]

    operations = [
        migrations.RunPython(set_lines, reverse),
    ]
