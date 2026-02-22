from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("apply", "0008_application_offer_letter_custom_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="application",
            name="rejected_offer_by_applicant",
            field=models.BooleanField(default=False),
        ),
    ]

