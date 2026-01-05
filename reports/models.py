from django.db import models

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