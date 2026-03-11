from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("apply", "0010_application_rejection_feedback_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="application",
            name="applicant_private_note",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="application",
            name="employer_private_note",
            field=models.TextField(blank=True, default=""),
        ),
    ]
