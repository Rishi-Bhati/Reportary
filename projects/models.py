from django.db import models
from components.models import Component
from uuid6 import uuid7

# Create your models here.

class Project(models.Model):

    #UUID Field
    uuid = models.UUIDField(
    default=uuid7,
    editable=False,
    unique=True,
    db_index=True,
    # null=True,
    # blank=True,
    )

    owner = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    link = models.URLField(max_length=200)
    description = models.TextField()
    org = models.ForeignKey('organisations.Organisation', on_delete=models.SET_NULL, null=True, blank=True)
    project_head = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_projects')
    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('org', 'Organization Members Only'),
        ('private', 'Private (Owner & Collaborators Only)'),
    ]
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='public')
    public = models.BooleanField(default=True)
    collaborators = models.ManyToManyField('accounts.User', related_name='collaborations')
    
    max_attachments = models.PositiveIntegerField(default=5)
    allowed_attachment_types = models.CharField(max_length=255, default=".jpg,.jpeg,.png,.pdf,.doc,.docx,.xls,.xlsx,.zip,.txt")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
    
    @property
    def components(self):
        """Get all components related to this project"""
        return self.project_components.all()