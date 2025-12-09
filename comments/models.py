from django.db import models
from django.conf import settings

# The Comment model represents a single comment made by a user on a report.
class Comment(models.Model):
    # The 'report' field is a ForeignKey to the 'Report' model in the 'reports' app.
    # This creates a many-to-one relationship: one report can have many comments.
    # on_delete=models.CASCADE means that if a report is deleted, all its comments will also be deleted.
    # The 'related_name="comments"' is crucial. It creates a reverse relationship on the Report model,
    # allowing us to access all comments for a report object using 'report.comments.all()'.
    # The lack of this was causing an AttributeError: 'Report' object has no attribute 'comments'.
    report = models.ForeignKey('reports.Report', on_delete=models.CASCADE, related_name='comments')
    
    # This ForeignKey links the comment to the user who wrote it.
    # We use settings.AUTH_USER_MODEL to refer to the User model, which is best practice in Django.
    commented_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    
    # This field stores the actual text of the comment.
    text = models.TextField()
    
    # This field was intended to control the visibility of the comment.
    # Based on the user request, it is not displayed on the front end.
    visibility = models.BooleanField(default=True)
    
    # This field automatically records the date and time when the comment is created.
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # This method provides a human-readable string representation of the comment object,
        # which is useful in the Django admin and for debugging.
        return f'Comment by {self.commented_by.username} on {self.report.title}'
