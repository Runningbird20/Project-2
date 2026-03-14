from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0029_skilloption"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="resume_file",
            field=models.FileField(blank=True, null=True, upload_to="profile_resumes/"),
        ),
    ]
