from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("jobposts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="jobpost",
            name="pay_range",
            field=models.CharField(default="", max_length=100),
            preserve_default=False,
        ),
    ]
