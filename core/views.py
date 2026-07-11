from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from projects.models import Project
from reports.models import Report
from accounts.models import User
from comments.models import Comment
from organisations.models import Organisation
from reports.models import SavedSearch


@login_required
def global_search(request):
    """Global search across Projects, Reports, Comments, and Organizations with rich filters & highlights."""
    q = request.GET.get('q', '').strip()
    
    # 1. Session-based Recent Searches (up to 5)
    recent_searches = request.session.get('recent_searches', [])
    if q:
        if q in recent_searches:
            recent_searches.remove(q)
        recent_searches.insert(0, q)
        request.session['recent_searches'] = recent_searches[:5]
        request.session.modified = True

    # 2. Retrieve Filter Parameters
    status = request.GET.get('status', '').strip()
    impact = request.GET.get('impact', '').strip()
    assignee_id = request.GET.get('assignee_id', '').strip()
    reporter_id = request.GET.get('reporter_id', '').strip()
    org_id = request.GET.get('org_id', '').strip()
    component_id = request.GET.get('component_id', '').strip()
    date_start = request.GET.get('date_start', '').strip()
    date_end = request.GET.get('date_end', '').strip()

    # Get user organizations for scoping permissions
    from organisations.services import get_user_organisations
    user_orgs = get_user_organisations(request.user) if request.user.is_authenticated else Organisation.objects.none()

    projects = Project.objects.all()
    reports = Report.objects.all()
    organisations = Organisation.objects.all()
    comments = Comment.objects.all()

    # 3. Apply Permissions Scoping
    if request.user.is_authenticated:
        projects = projects.filter(Q(public=True) | Q(owner=request.user) | Q(collaborators=request.user) | Q(org__in=user_orgs))
        reports = reports.filter(
            Q(project__public=True) & (
                Q(visibility=True) | Q(reported_by=request.user) | Q(project__collaborators=request.user) | Q(project__owner=request.user)
            ) |
            Q(project__org__isnull=False, project__org__in=user_orgs) |
            Q(project__public=False, project__org__isnull=True) & (
                Q(project__owner=request.user) | Q(project__collaborators=request.user) | Q(reported_by=request.user)
            )
        )
        organisations = organisations.filter(Q(owner=request.user) | Q(members=request.user))
        comments = comments.filter(
            Q(report__project__public=True) & (
                Q(report__visibility=True) | Q(report__reported_by=request.user) | Q(report__project__collaborators=request.user) | Q(report__project__owner=request.user)
            ) |
            Q(report__project__org__isnull=False, report__project__org__in=user_orgs) |
            Q(report__project__public=False, report__project__org__isnull=True) & (
                Q(report__project__owner=request.user) | Q(report__project__collaborators=request.user) | Q(report__reported_by=request.user)
            )
        )
    else:
        projects = projects.filter(public=True)
        reports = reports.filter(project__public=True, visibility=True)
        organisations = Organisation.objects.none()
        comments = comments.filter(report__project__public=True, report__visibility=True)

    # 4. Apply Text Search Query (only if q is provided)
    if q:
        projects = projects.filter(Q(title__icontains=q) | Q(description__icontains=q))
        reports = reports.filter(Q(title__icontains=q) | Q(description__icontains=q) | Q(steps__icontains=q) | Q(component__name__icontains=q))
        organisations = organisations.filter(Q(name__icontains=q) | Q(description__icontains=q))
        comments = comments.filter(text__icontains=q)

    # 5. Apply Specific Filters
    if status:
        reports = reports.filter(status=status)
        comments = comments.filter(report__status=status)
    if impact:
        reports = reports.filter(impact=impact)
        comments = comments.filter(report__impact=impact)
    if assignee_id:
        reports = reports.filter(assigned_to_id=assignee_id)
        comments = comments.filter(report__assigned_to_id=assignee_id)
    if reporter_id:
        reports = reports.filter(reported_by_id=reporter_id)
        comments = comments.filter(report__reported_by_id=reporter_id)
    if org_id:
        projects = projects.filter(org_id=org_id)
        reports = reports.filter(project__org_id=org_id)
        comments = comments.filter(report__project__org_id=org_id)
    if component_id:
        reports = reports.filter(component_id=component_id)
        comments = comments.filter(report__component_id=component_id)
    if date_start:
        reports = reports.filter(created_at__date__gte=date_start)
        comments = comments.filter(created_at__date__gte=date_start)
    if date_end:
        reports = reports.filter(created_at__date__lte=date_end)
        comments = comments.filter(created_at__date__lte=date_end)

    # 6. Extract highlighted item (if any) and exclude it from the sliced queries so it can be prepended
    highlight = request.GET.get('highlight', '').strip()
    highlight_type = None
    highlight_id = None
    if ':' in highlight:
        highlight_type, highlight_id = highlight.split(':', 1)

    highlighted_report = None
    highlighted_project = None
    highlighted_org = None
    highlighted_comment = None

    if highlight_type == 'report' and highlight_id:
        try:
            highlighted_report = Report.objects.filter(uuid=highlight_id).select_related('project', 'component', 'reported_by').first()
            if highlighted_report:
                reports = reports.exclude(uuid=highlight_id)
        except Exception:
            pass
    elif highlight_type == 'project' and highlight_id:
        try:
            highlighted_project = Project.objects.filter(uuid=highlight_id).select_related('org').first()
            if highlighted_project:
                projects = projects.exclude(uuid=highlight_id)
        except Exception:
            pass
    elif highlight_type == 'org' and highlight_id:
        try:
            highlighted_org = Organisation.objects.filter(uuid=highlight_id).first()
            if highlighted_org:
                organisations = organisations.exclude(uuid=highlight_id)
        except Exception:
            pass
    elif highlight_type == 'comment' and highlight_id:
        try:
            highlighted_comment = Comment.objects.filter(id=highlight_id).select_related('report', 'report__project', 'commented_by').first()
            if highlighted_comment:
                comments = comments.exclude(id=highlight_id)
        except Exception:
            pass

    # 7. Evaluate Querysets (and slice)
    projects = list(projects.select_related('org').distinct()[:25])
    reports = list(reports.select_related('project', 'component', 'reported_by').distinct()[:50])
    organisations = list(organisations.distinct()[:25])
    comments = list(comments.select_related('report', 'report__project', 'commented_by').distinct()[:50])

    # Fetch lookup data for select filter dropdowns
    filter_users = User.objects.all().order_by('username')
    filter_orgs = get_user_organisations(request.user) if request.user.is_authenticated else Organisation.objects.none()
    from components.models import Component
    filter_components = Component.objects.all().order_by('name')
    saved_searches = SavedSearch.objects.filter(user=request.user) if request.user.is_authenticated else SavedSearch.objects.none()

    context = {
        'q': q,
        'projects': projects,
        'reports': reports,
        'organisations': organisations,
        'comments': comments,
        'highlighted_report': highlighted_report,
        'highlighted_project': highlighted_project,
        'highlighted_org': highlighted_org,
        'highlighted_comment': highlighted_comment,
        'recent_searches': recent_searches,
        'saved_searches': saved_searches,
        'filter_users': filter_users,
        'filter_orgs': filter_orgs,
        'filter_components': filter_components,
        # Selected states for sticky filters input:
        'selected_status': status,
        'selected_impact': impact,
        'selected_assignee_id': int(assignee_id) if assignee_id.isdigit() else '',
        'selected_reporter_id': int(reporter_id) if reporter_id.isdigit() else '',
        'selected_org_id': int(org_id) if org_id.isdigit() else '',
        'selected_component_id': int(component_id) if component_id.isdigit() else '',
        'selected_date_start': date_start,
        'selected_date_end': date_end,
    }

    # 8. Realtime HTMX Swapping Check
    if request.headers.get('HX-Request') or request.GET.get('hx_request') == 'true':
        return render(request, 'search_results_partial.html', context)
        
    return render(request, 'search_results.html', context)


@login_required
def global_search_glimpse(request):
    """Return a minimal glimpse of search results for popdown dropdown menu."""
    q = request.GET.get('q', '').strip()
    recent_searches = request.session.get('recent_searches', [])
    
    projects = []
    reports = []
    organisations = []
    comments = []
    
    if q:
        # Scoping logic
        from organisations.services import get_user_organisations
        user_orgs = get_user_organisations(request.user) if request.user.is_authenticated else Organisation.objects.none()

        projects_qs = Project.objects.all()
        reports_qs = Report.objects.all()
        organisations_qs = Organisation.objects.all()
        comments_qs = Comment.objects.all()

        if request.user.is_authenticated:
            projects_qs = projects_qs.filter(Q(public=True) | Q(owner=request.user) | Q(collaborators=request.user) | Q(org__in=user_orgs))
            reports_qs = reports_qs.filter(
                Q(project__public=True) & (
                    Q(visibility=True) | Q(reported_by=request.user) | Q(project__collaborators=request.user) | Q(project__owner=request.user)
                ) |
                Q(project__org__isnull=False, project__org__in=user_orgs) |
                Q(project__public=False, project__org__isnull=True) & (
                    Q(project__owner=request.user) | Q(project__collaborators=request.user) | Q(reported_by=request.user)
                )
            )
            organisations_qs = organisations_qs.filter(Q(owner=request.user) | Q(members=request.user))
            comments_qs = comments_qs.filter(
                Q(report__project__public=True) & (
                    Q(report__visibility=True) | Q(report__reported_by=request.user) | Q(report__project__collaborators=request.user) | Q(report__project__owner=request.user)
                ) |
                Q(report__project__org__isnull=False, report__project__org__in=user_orgs) |
                Q(report__project__public=False, report__project__org__isnull=True) & (
                    Q(report__project__owner=request.user) | Q(report__project__collaborators=request.user) | Q(report__reported_by=request.user)
                )
            )
        else:
            projects_qs = projects_qs.filter(public=True)
            reports_qs = reports_qs.filter(project__public=True, visibility=True)
            organisations_qs = Organisation.objects.none()
            comments_qs = comments_qs.filter(report__project__public=True, report__visibility=True)

        # Apply query limits for glimpse dropdown preview
        projects = projects_qs.filter(Q(title__icontains=q) | Q(description__icontains=q)).select_related('org').distinct()[:3]
        reports = reports_qs.filter(Q(title__icontains=q) | Q(description__icontains=q) | Q(steps__icontains=q)).select_related('project', 'component').distinct()[:3]
        organisations = organisations_qs.filter(Q(name__icontains=q) | Q(description__icontains=q)).distinct()[:3]
        comments = comments_qs.filter(text__icontains=q).select_related('report', 'report__project', 'commented_by').distinct()[:3]

    context = {
        'q': q,
        'projects': projects,
        'reports': reports,
        'organisations': organisations,
        'comments': comments,
        'recent_searches': recent_searches,
    }
    return render(request, 'search_glimpse_partial.html', context)
