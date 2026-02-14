from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("jobposts", "0002_jobpost_pay_range"),
    ]

    operations = [
        migrations.AddField(
            model_name="jobpost",
            name="salary_max",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="jobpost",
            name="salary_min",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="jobpost",
            name="skills",
            field=models.CharField(blank=True, max_length=300),
        ),
        migrations.AddField(
            model_name="jobpost",
            name="visa_sponsorship",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="jobpost",
            name="work_setting",
            field=models.CharField(
                choices=[("remote", "Remote"), ("onsite", "On-site"), ("hybrid", "Hybrid")],
                default="onsite",
                max_length=20,
            ),
        ),
    ]
