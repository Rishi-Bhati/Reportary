from django.shortcuts import render, redirect, get_object_or_404
from reports.forms import ReportForm
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from projects.models import Project
from components.models import Component
from reports.models import Report
from comments.models import Comment
from comments.forms import CommentForm


# Create your views here.


def report_list(request, project_pk):
    """
    Displays a list of all reports for a specific project.
    """
    # Fetches the project object based on the primary key from the URL.
    project = get_object_or_404(Project, pk=project_pk)
    # Filters reports that belong to the fetched project.
    reports = Report.objects.filter(project=project)
    # Renders the 'report_list.html' template, passing the reports and project as context.
    return render(request, 'report_list.html', {'reports': reports, 'project': project})

def report_detail(request, project_pk, report_pk):
    """
    Displays the details of a single report, including its comments.
    """
    # Fetches the specific report, ensuring it belongs to the correct project.
    report = get_object_or_404(Report, project__pk=project_pk, pk=report_pk)
    # Gets the project from the report object.
    project = report.project

    # By default, fetch only visible comments.
    comments = Comment.objects.filter(report=report, visibility=True)

    # If the user is authenticated, they might be able to see hidden comments.
    if request.user.is_authenticated:
        # The project owner, the report's author, and the comment's author can see hidden comments.
        # We use Q objects to create a complex query for this logic.
        from django.db.models import Q
        is_privileged_user = request.user == project.owner or request.user == report.reported_by
        if is_privileged_user:
            # If the user is the project owner or reporter, show all comments for this report.
            comments = Comment.objects.filter(report=report)
        else:
            # Otherwise, show visible comments PLUS any hidden comments made by the current user.
            comments = Comment.objects.filter(
                Q(report=report) & (Q(visibility=True) | Q(commented_by=request.user))
            ).distinct()

    # Creates an empty instance of the comment form to be rendered in the template.
    comment_form = CommentForm()
    # Determines if the current user is the owner of the project.
    is_project_owner = False
    is_reporter = False
    is_commenter = False
    
    is_report_hidden = report.visibility 
    if request.user == project.owner:
        is_project_owner = True
    
    if request.user == report.reported_by:
        is_reporter = True
    
    for comment in comments:
        if request.user == comment.commented_by:
            is_commenter = True
            break
    # is_project_owner = request.user.is_authenticated and request.user == project.owner

    # Renders the 'report_detail.html' template with all the necessary context.
    return render(request, 'report_detail.html', {'report': report, 'project': project, 'comments': comments, 'comment_form': comment_form, 'is_project_owner': is_project_owner, 'is_reporter': is_reporter, 'is_commenter': is_commenter, 'is_report_hidden': is_report_hidden})

@login_required
def create_report(request, project_pk=None):    
    """
    View for creating a new report.
    
    Supports two different workflows:
    1. /reports/new/ - User selects a project from dropdown, then creates report
    2. /projects/<pk>/reports/new/ - Project is pre-selected from URL, user only fills other fields
    
    Args:
        project_pk: Optional project ID from URL. If provided, the project is pre-selected.
    """
    project = None
    
    # If a project_pk is provided in the URL (e.g., /projects/3/reports/new/)
    # fetch the project object. This represents the specific project the user wants to report on.
    if project_pk is not None:
        project = get_object_or_404(Project, pk=project_pk)

    if request.method == 'POST':
        # Form submission - create the report
        
        # Initialize form with POST data and pass the project
        # The form's __init__ will use the project parameter to:
        # - Remove the project field (if project was pre-selected)
        # - Filter components to only show those from this project
        form = ReportForm(request.POST, request.FILES, project=project)
        
        if form.is_valid():
            # Form validation passed
            # At this point, the form's clean() method has already verified
            # that a project exists (either from URL or form submission)
            
            report = form.save(commit=False)
            
            # Set the user who is reporting this issue
            report.reported_by = request.user
            
            # SECURITY FIX: Re-set the project from the URL parameter
            # Why this is crucial:
            # Even though the form's save() method already sets the project (if it came from URL),
            # this is an extra layer of security. If project came from URL (project_pk is set),
            # we ensure it's used, not any potentially tampered form data.
            #
            # Scenario 1: /projects/3/reports/new/
            #   - project = Project(pk=3) from URL
            #   - Form had no project field (removed in form.__init__)
            #   - Form.save() already set report.project = 3
            #   - This line re-confirms it: report.project = 3
            #
            # Scenario 2: /reports/new/
            #   - project = None (not in URL)
            #   - Form had project field, user selected it
            #   - Form.save() didn't override the project (self.project is None)
            #   - This line doesn't execute (if project is None)
            #   - So report.project keeps the value from form submission
            if project:
                report.project = project
            
            # Save the report to the database
            report.save()

            # After successful creation, redirect to the report detail page
            # This shows the newly created report
            return redirect('projects:reports:report_detail', project_pk=report.project.pk, report_pk=report.pk)
    else:
        # GET request - display the form
        
        # Initialize an empty form and pass the project parameter
        # The form will:
        # - Remove the project field if project_pk is provided
        # - Show all projects if project_pk is not provided
        form = ReportForm(project=project)
        
    return render(request, 'create_report.html', {'form': form, 'project': project})


def get_components(request):
    project_id = request.GET.get('project_id')
    if not project_id:
        return JsonResponse([], safe=False)
    components = list(Component.objects.filter(project_id=project_id).values('id', 'name'))
    return JsonResponse(components, safe=False)
