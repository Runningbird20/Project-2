from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0020_profile_structured_address_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="company_culture",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="profile",
            name="company_perks",
            field=models.TextField(blank=True),
        ),
    ]
