from django.db import models

# Create your models here.

class Comment(models.Model):
    report = models.ForeignKey('reports.Report', on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    display_name = models.CharField(max_length=100)
    content = models.TextField()
    visibility = models.CharField(max_length=20, choices=[('public', 'Public'), ('private', 'Private')], default='public')
    edited = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Comment {self.id} - {self.content[:20]}"