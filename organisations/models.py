from django.db import models
from uuid6 import uuid7

# Create your models here.

class Organisation(models.Model):

    #UUID Field
    uuid = models.UUIDField(
    default=uuid7,
    editable=False,
    unique=True,
    db_index=True,
    # null=True,
    # blank=True,
    )

    owner = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="organisations")

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    
    domain = models.CharField(max_length=255, blank=True, null=True)
    verified = models.BooleanField(default=False)
    # verify_method = models.CharField(max_length=255, blank=True, null=True)
    # verify_token = models.CharField(max_length=255, blank=True, null=True)

    members = models.ManyToManyField("accounts.User", related_name="organisation_members", blank=True)
    # admins = models.ManyToManyField("accounts.User", related_name="admin_organisations", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name