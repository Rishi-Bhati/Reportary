from django.db import models
from uuid6 import uuid7

# Create your models here.

class Component(models.Model):
    
    #UUID Field
    uuid = models.UUIDField(
    default=uuid7,
    editable=False,
    unique=True,
    db_index=True,
    # null=True,
    # blank=True,
    )

    name = models.CharField(max_length=100)
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE, related_name='project_components')
    description = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name