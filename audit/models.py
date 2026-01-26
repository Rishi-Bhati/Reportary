from django.db import models
from django.contrib.auth import get_user_model

# Create your models here.


User = get_user_model()

class AuditLog(models.Model):
    ACTION_CHOICES = (
        ("create", "Create"),
        ("update", "Update"),
        ("delete", "Delete"),
    )

    actor = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL
    )

    action = models.CharField(max_length=20, choices=ACTION_CHOICES)

    entity_type = models.CharField(max_length=50)
    entity_id = models.CharField(max_length=36)  # works for UUID/int

    parent_type = models.CharField(max_length=50, null=True, blank=True)
    parent_id = models.CharField(max_length=36, null=True, blank=True)  # works for UUID/int

    field_name = models.CharField(max_length=100, null=True, blank=True)
    old_value = models.TextField(null=True, blank=True)
    new_value = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.entity_type}:{self.entity_id} {self.action}"
