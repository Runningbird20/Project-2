from django.db import models
from django.contrib.auth.models import User

class Apply(models.Model):
    company = models.CharField(max_length=100)
    title = models.CharField(max_length=100)
    salary_range = models.CharField(max_length=50)
    logo = models.ImageField(upload_to="logos/", blank=True, null=True)

    def __str__(self):
        return f"{self.title} @ {self.company}"
    
class Application(models.Model):

    STATUS_CHOICES = [
        ("applied", "Applied"),
        ("review", "Under Review"),
        ("interview", "Interview"),
        ("offer", "Offer"),
        ("closed", "Closed"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    job = models.ForeignKey(Apply, on_delete=models.CASCADE)
    note = models.TextField(blank=True)
    resume_type = models.CharField(
        max_length=20,
        choices=[("profile", "Profile Resume"), ("uploaded", "Uploaded Resume")]
    )
    applied_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="applied"
    )
    
    class Meta:
        unique_together = ("user", "job")
