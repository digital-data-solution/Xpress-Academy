# Data migration — closes a gap flagged (but not fixed) earlier in the
# build: "Advanced" was published with no prerequisite, so a learner
# could buy straight into it without ever completing Intermediate.
# Explicit user instruction now: every Advanced-tier course must gate
# behind its Intermediate, every Intermediate behind its Foundation.

from django.db import migrations


def gate_advanced(apps, schema_editor):
    Course = apps.get_model("catalog", "Course")
    intermediate = Course.objects.filter(slug="practical-dog-breeding-intermediate").first()
    if intermediate:
        Course.objects.filter(slug="practical-dog-breeding-advanced").update(prerequisite=intermediate)


def reverse(apps, schema_editor):
    Course = apps.get_model("catalog", "Course")
    Course.objects.filter(slug="practical-dog-breeding-advanced").update(prerequisite=None)


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0013_set_webhook_line_for_existing_programmes'),
    ]

    operations = [
        migrations.RunPython(gate_advanced, reverse),
    ]
