from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0019_profile_location_max_length"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="address_line_1",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="profile",
            name="address_line_2",
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AddField(
            model_name="profile",
            name="city",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AddField(
            model_name="profile",
            name="country",
            field=models.CharField(blank=True, default="United States", max_length=100),
        ),
        migrations.AddField(
            model_name="profile",
            name="postal_code",
            field=models.CharField(blank=True, max_length=20),
        ),
        migrations.AddField(
            model_name="profile",
            name="state",
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
