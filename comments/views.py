from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import HttpResponse
from .models import Comment
# The Report model is imported from the 'reports' app.
# This is necessary because a comment is associated with a report.
# The previous ImportError occurred because 'Report' was being imported from '.models' (i.e., 'comments.models'), where it is not defined.
from reports.models import Report
from .forms import CommentForm

# The '@require_POST' decorator ensures that this view can only be accessed with a POST request.
# This is a security measure to prevent users from adding comments via GET requests.
@require_POST
# The '@login_required' decorator ensures that only logged-in users can add comments.
@login_required
def add_comment(request, report_pk):
    """
    This view handles the creation of a new comment for a specific report.
    It's triggered by an HTMX POST request from the report detail page.
    """
    # First, we get the report object using the primary key from the URL.
    # If the report does not exist, it will return a 404 Not Found error.
    report = get_object_or_404(Report, pk=report_pk)
    
    # We instantiate the CommentForm with the POST data from the request.
    form = CommentForm(request.POST)
    
    # We check if the form is valid.
    if form.is_valid():
        # If the form is valid, we create a Comment object but don't save it to the database yet (commit=False).
        comment = form.save(commit=False)
        # We assign the report and the user who made the comment.
        comment.report = report
        comment.commented_by = request.user
        # Now we save the comment to the database.
        comment.save()
        # Finally, we render the new comment using a partial template and return it as the response.
        # HTMX will then use this response to update the comments section on the page.
        return render(request, 'comments/partials/comment.html', {'comment': comment})
        
    # If the form is not valid, we return a 400 Bad Request response.
    return HttpResponse(status=400)