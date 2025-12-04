from django.shortcuts import render, redirect, get_object_or_404
from reports.forms import ReportForm
from projects.models import Project
from reports.models import Report


# Create your views here.


def report_list(request, pk):
    project = get_object_or_404(Project, pk=pk)
    reports = Report.objects.all().filter(project=project)
    return render(request, 'report_list.html', {'reports': reports, 'project': project})

def report_detail(request, pk, report_pk):
    report = get_object_or_404(Report, project__pk=pk, pk=report_pk)
    project = report.project
    return render(request, 'report_detail.html', {'report': report, 'project': project})

def create_report(request, pk=None):

    project = None
    if pk is not None:
        project = get_object_or_404(Project, pk=pk)

    user = request.user

    if request.method == 'POST':
        form = ReportForm(request.POST)
        # prevent user from changing project when pk was passed
        if project and 'project' in form.fields:
            form.fields['project'].initial = project
            form.fields['project'].disabled = True

        if form.is_valid():
            report = form.save(commit=False)
            if project:
                report.project = project
            report.reported_by = user
            report.save()
            if project:
                return redirect('projects:project_detail', pk=project.pk)
            return redirect('report_list')
    else:
        initial = {}
        if project:
            initial['project'] = project
        form = ReportForm(initial=initial)
        if project and 'project' in form.fields:
            form.fields['project'].disabled = True
        
    return render(request, 'create_report.html', {'form': form, 'project': project})
