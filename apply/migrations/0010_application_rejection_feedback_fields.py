from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("apply", "0009_application_rejected_offer_by_applicant"),
    ]

    operations = [
        migrations.AddField(
            model_name="application",
            name="rejection_feedback_note",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="application",
            name="rejection_feedback_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="application",
            name="rejection_feedback_template",
            field=models.CharField(blank=True, default="", max_length=40),
        ),
    ]
