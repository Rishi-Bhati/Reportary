from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from projects.models import Project
from reports.models import Report
from django.db.models import Q

@login_required
def dashboard(request):
    user = request.user
    
    from organisations.services import get_user_organisations
    user_orgs = get_user_organisations(user)
    
    # Fetch projects where user is owner (personal/org), project head (org), or collaborator
    projects = Project.objects.filter(
        Q(org__isnull=True, owner=user) |
        Q(org__isnull=False, org__owner=user) |
        Q(org__isnull=False, project_head=user) |
        Q(collaborators=user)
    ).select_related('org').distinct().order_by('-updated_at')[:5]
    
    # Fetch assigned or reported reports
    assigned_reports = Report.objects.filter(assigned_to=user).select_related('project').order_by('-updated_at')[:5]
    my_reports = Report.objects.filter(reported_by=user).select_related('project').order_by('-created_at')[:5]
    
    # Fetch organisations
    owned_organisations = user.organisations.all()
    member_organisations = user.organisation_members.all()

    context = {
        'projects': projects,
        'assigned_reports': assigned_reports,
        'my_reports': my_reports,
        'owned_organisations': owned_organisations,
        'member_organisations': member_organisations,
    }
    
    return render(request, "dashboard.html", context)
