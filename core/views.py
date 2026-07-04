from django.shortcuts import render
from django.db.models import Q
from projects.models import Project
from reports.models import Report
from accounts.models import User


def global_search(request):
    """Global search across Projects, Reports and Users."""
    q = request.GET.get('q', '').strip()
    projects = []
    reports = []
    users = []

    if q:
        if request.user.is_authenticated:
            from organisations.services import get_user_organisations
            user_orgs = get_user_organisations(request.user)
            
            projects = Project.objects.filter(
                Q(title__icontains=q) | Q(description__icontains=q)
            ).filter(
                Q(public=True) |
                Q(owner=request.user) |
                Q(collaborators=request.user) |
                Q(org__in=user_orgs)
            ).select_related('org').distinct()[:25]
            
            reports = Report.objects.filter(
                Q(title__icontains=q) | Q(description__icontains=q) | Q(component__name__icontains=q)
            ).filter(
                Q(project__public=True) & (
                    Q(visibility=True) | Q(reported_by=request.user) | Q(project__collaborators=request.user) | Q(project__owner=request.user)
                ) |
                Q(project__org__isnull=False, project__org__in=user_orgs) |
                Q(project__public=False, project__org__isnull=True) & (
                    Q(project__owner=request.user) | Q(project__collaborators=request.user) | Q(reported_by=request.user)
                )
            ).select_related('project', 'component').distinct()[:50]
        else:
            projects = Project.objects.filter(
                Q(title__icontains=q) | Q(description__icontains=q)
            ).filter(public=True).select_related('org').distinct()[:25]
            
            reports = Report.objects.filter(
                Q(title__icontains=q) | Q(description__icontains=q) | Q(component__name__icontains=q),
                project__public=True,
                visibility=True
            ).select_related('project', 'component').distinct()[:50]

        users = User.objects.filter(Q(username__icontains=q) | Q(email__icontains=q)).distinct()[:25]

    context = {
        'q': q,
        'projects': projects,
        'reports': reports,
        'users': users,
    }
    return render(request, 'search_results.html', context)
