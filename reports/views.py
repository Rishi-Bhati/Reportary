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
    project = None
    if project_pk is not None:
        project = get_object_or_404(Project, pk=project_pk)

    if request.method == 'POST':
        # Pass project to the form
        form = ReportForm(request.POST, request.FILES, project=project)
        
        if form.is_valid():
            report = form.save(commit=False)
            report.reported_by = request.user
            # Set the project based on URL parameter (not from form to prevent tampering)
            if project:
                report.project = project
            report.save()

            # Redirect to the newly created report's detail page
            return redirect('projects:reports:report_detail', project_pk=report.project.pk, report_pk=report.pk)
    else:
        # For a GET request, pass project to form if it exists in the URL
        form = ReportForm(project=project)
        
    return render(request, 'create_report.html', {'form': form, 'project': project})


def get_components(request):
    project_id = request.GET.get('project_id')
    if not project_id:
        return JsonResponse([], safe=False)
    components = list(Component.objects.filter(project_id=project_id).values('id', 'name'))
    return JsonResponse(components, safe=False)
