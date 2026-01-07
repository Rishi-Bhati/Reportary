from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from projects.models import Project
from reports.models import Report
from django.db.models import Q

@login_required
def dashboard(request):
    user = request.user
    
    # Fetch projects where user is owner or collaborator
    projects = Project.objects.filter(
        Q(owner=user) | Q(collaborators=user)
    ).distinct().order_by('-updated_at')[:5]
    
    # Fetch assigned or reported reports
    assigned_reports = Report.objects.filter(assigned_to=user).order_by('-updated_at')[:5]
    my_reports = Report.objects.filter(reported_by=user).order_by('-created_at')[:5]
    
    context = {
        'projects': projects,
        'assigned_reports': assigned_reports,
        'my_reports': my_reports,
    }
    
    return render(request, "dashboard.html", context)
