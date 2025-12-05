from django.shortcuts import render, redirect, get_object_or_404
from reports.forms import ReportForm
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from projects.models import Project
from components.models import Component
from reports.models import Report


# Create your views here.


def report_list(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk)
    reports = Report.objects.filter(project=project)
    return render(request, 'report_list.html', {'reports': reports, 'project': project})

def report_detail(request, project_pk, report_pk):
    report = get_object_or_404(Report, project__pk=project_pk, pk=report_pk)
    project = report.project
    return render(request, 'report_detail.html', {'report': report, 'project': project})

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
