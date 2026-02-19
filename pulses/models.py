from django.db import models
from django.contrib.auth.models import User

class Pulse(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="pulses")
    video = models.FileField(upload_to="pulses/videos/")
    caption = models.CharField(max_length=220, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]  # newest first

    def __str__(self):
        return f"Pulse by {self.user.username} ({self.created_at:%Y-%m-%d})"
