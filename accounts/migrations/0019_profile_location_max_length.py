from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0018_merge_20260218_1741"),
    ]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="location",
            field=models.CharField(blank=True, max_length=255),
        ),
    ]
