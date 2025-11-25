from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):

    USER_TYPES = (
        ("normal", "Normal User"),
        ("dev", "Developer"),
        ("cp", "Organisation Contact Person"),
    )

    # Overrides
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)

    # Required fields
    type = models.CharField(max_length=20, choices=USER_TYPES, default="normal")

    # Organisation link (if user is CP)
    # organisation = models.ForeignKey(
    #     "organisations.Organisation",
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True
    # )
    organisation = models.IntegerField(null=True, blank=True)

    is_cp = models.BooleanField(default=False)

    business_email = models.EmailField(null=True, blank=True)
    cp_role = models.CharField(max_length=100, null=True, blank=True)

    # Developer-only fields
    github_oauth_id = models.CharField(max_length=255, null=True, blank=True)
    github_verified = models.BooleanField(default=False)

    # Django already gives: password, date_joined, last_login
    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        return self.username
