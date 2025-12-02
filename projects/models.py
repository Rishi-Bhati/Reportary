from django.db import models
from components.models import Component


# Create your models here.

class Project(models.Model):
    owner = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    link = models.URLField(max_length=200)
    description = models.TextField()
    public = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
    
    @property
    def components(self):
        """Get all components related to this project"""
        return self.component_set.all()