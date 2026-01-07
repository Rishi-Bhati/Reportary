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
        projects = Project.objects.filter(
            Q(title__icontains=q) | Q(description__icontains=q)
        ).filter(public=True).distinct()[:25]

        # Reports: respect visibility / access: show visible reports OR reports by the user OR project collaborators/owners
        if request.user.is_authenticated:
            reports = Report.objects.filter(
                Q(title__icontains=q) | Q(description__icontains=q) | Q(component__name__icontains=q)
            ).filter(
                Q(visibility=True) | Q(reported_by=request.user) | Q(project__collaborators=request.user) | Q(project__owner=request.user)
            ).select_related('project').distinct()[:50]
        else:
            reports = Report.objects.filter(
                Q(title__icontains=q) | Q(description__icontains=q) | Q(component__name__icontains=q),
                visibility=True
            ).select_related('project').distinct()[:50]

        users = User.objects.filter(Q(username__icontains=q) | Q(email__icontains=q)).distinct()[:25]

    context = {
        'q': q,
        'projects': projects,
        'reports': reports,
        'users': users,
    }
    return render(request, 'search_results.html', context)
