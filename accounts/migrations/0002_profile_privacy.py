from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="visible_to_recruiters",
            field=models.BooleanField(default=True, help_text="Allow recruiters to view your profile."),
        ),
        migrations.AddField(
            model_name="profile",
            name="show_headline",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="profile",
            name="show_skills",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="profile",
            name="show_education",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="profile",
            name="show_work_experience",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="profile",
            name="show_links",
            field=models.BooleanField(default=True),
        ),
    ]
