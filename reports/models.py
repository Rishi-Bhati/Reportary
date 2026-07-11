from django.db import models
from uuid6 import uuid7

# Create your models here.


class Report(models.Model):

    FREQ_CHOICES = (
        ('once', 'Once'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    )

    IMPACT_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    )

    SEVERITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    )

    STATUS_CHOICES = (
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('resolved', 'Resolved'),
        ('closed', 'Closed'),
    )
    #UUID Field
    uuid = models.UUIDField(
    default=uuid7,
    editable=False,
    unique=True,
    db_index=True,
    # null=True,
    # blank=True,
    )
    
    title = models.CharField(max_length=200)
    project = models.ForeignKey('projects.Project', on_delete=models.CASCADE)
    component = models.ForeignKey('components.Component', on_delete=models.CASCADE, null=True, blank=True)
    reported_by = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    description = models.TextField()
    steps = models.TextField()
    
    frequency = models.CharField(max_length=20, choices=FREQ_CHOICES, default='once')
    impact = models.CharField(max_length=20, choices=IMPACT_CHOICES, default='low')
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='low')

    attatchment = models.FileField(upload_to='reports/', null=True, blank=True)
    visibility = models.BooleanField(default=True)

    assigned_to = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_reports')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='open')


    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    @property
    def safe_attatchment_size(self):
        if self.attatchment:
            try:
                return self.attatchment.size
            except Exception:
                return None
        return None


class ReportBookmark(models.Model):
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='report_bookmarks')
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='bookmarked_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'report')

    def __str__(self):
        return f"{self.user.username} bookmarked {self.report.title}"


class ReportFollower(models.Model):
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='following_reports')
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'report')

    def __str__(self):
        return f"{self.user.username} follows {self.report.title}"


class ReportAttachment(models.Model):
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='attachments')
    file = models.FileField(upload_to='reports/attachments/')
    filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Attachment for {self.report.title}: {self.filename}"


class SavedSearch(models.Model):
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='saved_searches')
    name = models.CharField(max_length=100)
    query = models.CharField(max_length=255, blank=True)
    filters = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}'s search: {self.name}"