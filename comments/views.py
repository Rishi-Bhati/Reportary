from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_http_methods
from django.http import HttpResponse
from .models import Comment
# The Report model is imported from the 'reports' app.
# This is necessary because a comment is associated with a report.
# The previous ImportError occurred because 'Report' was being imported from '.models' (i.e., 'comments.models'), where it is not defined.
from reports.models import Report
from projects.models import Project
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
        return render(request, 'comments/partials/comment.html', {'comment': comment, 'report': report})
        
    # If the form is not valid, we return a 400 Bad Request response.
    return HttpResponse(status=400)


# The '@login_required' decorator ensures that only logged-in users can edit comments.
@login_required
def edit_comment(request, report_pk, comment_pk):
    """
    This view handles both displaying the edit form (GET) and processing the
    submission of the form (POST) for editing a comment.
    """
    # Retrieve the report and the specific comment to be edited.
    # It's crucial to ensure the comment exists and belongs to the current user.
    report = get_object_or_404(Report, pk=report_pk)
    comment = get_object_or_404(Comment, pk=comment_pk, commented_by=request.user, report=report)

    # Requirement: A hidden comment cannot be edited.
    if not comment.visibility:
        return HttpResponse(status=403, content="Cannot edit a hidden comment.")
    
    # If the request is a POST, it means the user is submitting the edited comment.
    if request.method == 'POST':
        # We populate the form with the submitted data and the existing comment instance.
        form = CommentForm(request.POST, instance=comment)
        if form.is_valid():
            # If the form is valid, we save the changes.
            edited_comment = form.save(commit=False)
            edited_comment.is_edited = True
            edited_comment.save()
            # After saving, we render the updated comment content.
            # This is sent back to the browser and HTMX will use it to update the page.
            return render(request, 'comments/partials/comment_content.html', {'comment': edited_comment, 'report': report})
    # If the request is a GET, it means the user wants to see the edit form.
    else:
        # We create an instance of the form, populated with the existing comment's data.
        form = CommentForm(instance=comment)
        
    # For a GET request, we render the form that allows the user to edit the comment.
    return render(request, 'comments/partials/edit_comment_form.html', {'form': form, 'comment': comment, 'report': report})

@login_required
def cancel_edit_comment(request, report_pk, comment_pk):
    """
    This view handles the cancellation of an edit comment operation.
    It returns the original comment content.
    """
    report = get_object_or_404(Report, pk=report_pk)
    comment = get_object_or_404(Comment, pk=comment_pk, report=report)
    return render(request, 'comments/partials/comment_content.html', {'comment': comment, 'report': report})


@require_POST
@login_required
def toggle_comment_visibility(request, report_pk, comment_pk):
    """
    This view handles toggling the visibility of a comment.
    Only the project owner can perform this action.
    """
    report = get_object_or_404(Report, pk=report_pk)
    
    # Security check: Only the project owner can hide a comment.
    if request.user != report.project.owner:
        # Return a 403 Forbidden response if the user is not the project owner.
        return HttpResponse(status=403)

    comment = get_object_or_404(Comment, pk=comment_pk, report=report)

    # Toggle the visibility status.
    comment.visibility = not comment.visibility
    comment.save()

    # Return the updated comment partial. HTMX will swap this into the DOM.
    # We pass project to the template context so the hide/unhide button renders correctly.
    return render(request, 'comments/partials/comment.html', {'comment': comment, 'report': report, 'project': report.project})
