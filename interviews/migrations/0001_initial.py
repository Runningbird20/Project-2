from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("apply", "0004_alter_application_status"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="InterviewSlot",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("start_at", models.DateTimeField()),
                ("end_at", models.DateTimeField()),
                ("meeting_link", models.URLField(blank=True)),
                ("notes", models.TextField(blank=True)),
                (
                    "status",
                    models.CharField(
                        choices=[("open", "Open"), ("booked", "Booked"), ("canceled", "Canceled")],
                        default="open",
                        max_length=20,
                    ),
                ),
                ("proposed_at", models.DateTimeField(auto_now_add=True)),
                ("booked_at", models.DateTimeField(blank=True, null=True)),
                ("calendar_uid", models.CharField(blank=True, max_length=120, unique=True)),
                (
                    "applicant",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="applicant_interview_slots",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "application",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="interview_slots",
                        to="apply.application",
                    ),
                ),
                (
                    "booked_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="booked_interview_slots",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "employer",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="proposed_interview_slots",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["start_at"],
            },
        ),
    ]

