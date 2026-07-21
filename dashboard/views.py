from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q, F, Count
import datetime
from django.utils import timezone
from projects.models import Project
from reports.models import Report
from notifications.models import Invitation

@login_required
def dashboard(request):
    """
    Renders the quick-loading dashboard skeleton shell immediately.
    Data is loaded asynchronously via HTMX calls.
    """
    return render(request, "dashboard.html")

@login_required
def dashboard_overview(request):
    """
    Renders the overview tab content asynchronously.
    """
    user = request.user
    
    # 1. FETCH OVERVIEW DATA
    # Fetch projects where user is owner, project head, or collaborator
    projects = Project.objects.filter(
        Q(org__isnull=True, owner=user) |
        Q(org__isnull=False, org__owner=user) |
        Q(org__isnull=False, project_head=user) |
        Q(collaborators=user)
    ).select_related('org').distinct().order_by('-updated_at')[:5]
    
    # Fetch reports assigned to me
    assigned_reports_list = Report.objects.filter(assigned_to=user).select_related('project').order_by('-updated_at')[:5]
    assigned_reports_count = Report.objects.filter(assigned_to=user).count()
    
    # Fetch reports reported by me
    reported_reports_list = Report.objects.filter(reported_by=user).select_related('project').order_by('-created_at')[:5]
    reported_reports_count = Report.objects.filter(reported_by=user).count()
    
    # Fetch recently viewed reports from session
    recently_viewed_uuids = request.session.get('recently_viewed_reports', [])
    recently_viewed_reports = []
    if recently_viewed_uuids:
        reports_dict = {str(r.uuid): r for r in Report.objects.filter(uuid__in=recently_viewed_uuids).select_related('project')}
        for uuid_str in recently_viewed_uuids:
            if uuid_str in reports_dict:
                recently_viewed_reports.append(reports_dict[uuid_str])
                
    # Fetch pending invitations
    pending_actions = Invitation.objects.filter(invited_user=user, status='pending').select_related('project', 'organisation', 'invited_by')
    pending_actions_count = pending_actions.count()

    # Calculate average resolution time for overview metric
    accessible_projects = Project.objects.filter(
        Q(visibility='public') |
        Q(owner=user) |
        Q(project_head=user) |
        Q(collaborators=user) |
        Q(org__members=user)
    ).distinct()
    
    accessible_reports = Report.objects.filter(project__in=accessible_projects).distinct()
    
    from django.db.models import Avg, ExpressionWrapper, DurationField
    avg_duration = accessible_reports.filter(
        status='resolved',
        updated_at__gt=F('created_at')
    ).aggregate(
        avg_time=Avg(ExpressionWrapper(F('updated_at') - F('created_at'), output_field=DurationField()))
    )['avg_time']

    if avg_duration is not None:
        avg_seconds = avg_duration.total_seconds()
        days = int(avg_seconds // 86400)
        hours = int((avg_seconds % 86400) // 3600)
        if days > 0:
            avg_resolution_time = f"{days}d {hours}h"
        else:
            avg_resolution_time = f"{hours}h"
    else:
        avg_resolution_time = "N/A"

    # Fetch organisations
    owned_organisations = user.organisations.all()
    member_organisations = user.organisation_members.exclude(owner=user)

    context = {
        'projects': projects,
        'assigned_reports': assigned_reports_list,
        'assigned_reports_count': assigned_reports_count,
        'my_reports': reported_reports_list,
        'my_reports_count': reported_reports_count,
        'recently_viewed_reports': recently_viewed_reports,
        'pending_actions': pending_actions,
        'pending_actions_count': pending_actions_count,
        'avg_resolution_time': avg_resolution_time,
        'owned_organisations': owned_organisations,
        'member_organisations': member_organisations,
    }
    
    return render(request, "dashboard/partials/overview_partial.html", context)

@login_required
def dashboard_analytics(request):
    """
    Renders the analytics tab content and chart data asynchronously.
    """
    user = request.user
    
    # Get all projects the user is authorized to view
    accessible_projects = Project.objects.filter(
        Q(visibility='public') |
        Q(owner=user) |
        Q(project_head=user) |
        Q(collaborators=user) |
        Q(org__members=user)
    ).distinct()
    
    accessible_reports = Report.objects.filter(project__in=accessible_projects).distinct()
    total_reports_count = accessible_reports.count()
    
    # Open vs Closed status counts
    open_count = accessible_reports.filter(status__in=['open', 'in_progress']).count()
    closed_count = accessible_reports.filter(status__in=['resolved', 'closed']).count()
    
    # Severity distribution
    severity_counts = {
        'critical': accessible_reports.filter(impact='critical').count(),
        'high': accessible_reports.filter(impact='high').count(),
        'medium': accessible_reports.filter(impact='medium').count(),
        'low': accessible_reports.filter(impact='low').count()
    }
    
    # Reports by component
    component_stats = accessible_reports.filter(component__isnull=False).values('component__name').annotate(count=Count('id')).order_by('-count')[:5]
    component_labels = [item['component__name'] for item in component_stats]
    component_data = [item['count'] for item in component_stats]
    
    # Most active projects
    active_projects = accessible_reports.values('project__title', 'project__uuid').annotate(count=Count('id')).order_by('-count')[:5]
    
    # Most active contributors
    active_contributors = accessible_reports.filter(assigned_to__isnull=False).values('assigned_to__username').annotate(count=Count('id')).order_by('-count')[:5]
    
    # Reports over time (last 30 days)
    thirty_days_ago = timezone.now() - datetime.timedelta(days=30)
    recent_reports = accessible_reports.filter(created_at__gte=thirty_days_ago).order_by('created_at')
    
    time_map = {}
    for r in recent_reports:
        date_str = r.created_at.strftime('%Y-%m-%d')
        time_map[date_str] = time_map.get(date_str, 0) + 1
        
    time_labels = []
    time_data = []
    current_date = timezone.now().date() - datetime.timedelta(days=29)
    for _ in range(30):
        date_str = current_date.strftime('%Y-%m-%d')
        label_str = current_date.strftime('%b %d')
        time_labels.append(label_str)
        time_data.append(time_map.get(date_str, 0))
        current_date += datetime.timedelta(days=1)

    context = {
        'total_reports_count': total_reports_count,
        'open_count': open_count,
        'closed_count': closed_count,
        'severity_counts': severity_counts,
        'component_labels': component_labels,
        'component_data': component_data,
        'active_projects': active_projects,
        'active_contributors': active_contributors,
        'time_labels': time_labels,
        'time_data': time_data,
    }
    
    return render(request, "dashboard/partials/analytics_partial.html", context)
