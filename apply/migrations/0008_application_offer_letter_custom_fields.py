from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("apply", "0007_application_response_tracking_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="application",
            name="offer_additional_terms",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="application",
            name="offer_compensation",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="application",
            name="offer_letter_body",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="application",
            name="offer_letter_title",
            field=models.CharField(blank=True, max_length=200),
        ),
        migrations.AddField(
            model_name="application",
            name="offer_response_deadline",
            field=models.CharField(blank=True, max_length=120),
        ),
        migrations.AddField(
            model_name="application",
            name="offer_start_date",
            field=models.CharField(blank=True, max_length=120),
        ),
    ]
