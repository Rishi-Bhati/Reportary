from django.db import models


class Announcement(models.Model):
    """
    Site-wide announcements shown as a dismissable banner to all logged-in users.
    Only Django superusers can create/edit these (enforced via admin registration).
    """
    LEVEL_CHOICES = [
        ('info', 'Info (Blue)'),
        ('warning', 'Warning (Yellow)'),
        ('critical', 'Critical (Red)'),
        ('success', 'Success (Green)'),
    ]

    title = models.CharField(max_length=200)
    body = models.TextField()
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, default='info')
    is_active = models.BooleanField(default=True, help_text="Controls whether this announcement is visible to users.")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True,
        help_text="Optional. Automatically stop showing after this date/time.")

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_level_display()}] {self.title}"
