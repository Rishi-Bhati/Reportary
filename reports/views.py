from django.shortcuts import render, redirect, get_object_or_404
from reports.forms import ReportForm
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from projects.models import Project
from components.models import Component
from reports.models import Report
from comments.models import Comment
from comments.forms import CommentForm
from django.db.models import Q
import rules.views as rules
from accounts.models import User
import rules.views as rules



# Create your views here.


def report_list(request, project_pk=None):
    """
    Displays a list of all reports for a specific project.
    """
    # Fetches the project object based on the primary key from the URL.
    project = get_object_or_404(Project, pk=project_pk)
    # Filters reports that belong to the fetched project.

    base_qs = Report.objects.filter(project=project).select_related('reported_by').distinct()

    if request.user.is_authenticated:
        # Project owners and project members can see all reports
        if rules.is_project_owner(request.user, project) or rules.is_project_member(request.user, project):
            reports = base_qs
        else:
            # Non-members can see visible reports and any reports they reported themselves
            reports = base_qs.filter(Q(visibility=True) | Q(reported_by=request.user))
    else:
        # Anonymous users only see visible reports
        reports = base_qs.filter(visibility=True)

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
    is_project_owner = rules.is_project_owner(request.user, project)
    is_reporter = rules.is_reporter(request.user, report)
    user_can_change_status = rules.can_change_status(request.user, report)
    
    is_report_hidden = report.visibility == False
    is_commenter = False
    for comment in comments:
        is_commenter = rules.is_commenter(request.user, comment)
    
    all_users = User.objects.all()

    # Renders the 'report_detail.html' template with all the necessary context.
    return render(request, 'report_detail.html', {
        'report': report, 
        'project': project, 
        'comments': comments, 
        'comment_form': comment_form, 
        'is_project_owner': is_project_owner, 
        'is_reporter': is_reporter, 
        'is_commenter': is_commenter, 
        'is_report_hidden': is_report_hidden,
        'all_users': all_users,
        'status_choices': Report.STATUS_CHOICES,
        'impact_choices': Report.IMPACT_CHOICES,
        'can_change_status': user_can_change_status,
        })

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
    
    if project_pk is not None:
        project = get_object_or_404(Project, pk=project_pk)

    if request.method == 'POST':
        form = ReportForm(request.POST, request.FILES, project=project)
        
        if form.is_valid():
            report = form.save(commit=False)
            report.reported_by = request.user
            if project:
                report.project = project
            report.assigned_to = report.project.owner
            report.save()
            return redirect('projects:reports:report_detail', project_pk=report.project.pk, report_pk=report.pk)
    else:
        form = ReportForm(project=project)
        
    return render(request, 'create_report.html', {'form': form, 'project': project})


def get_components(request):
    project_id = request.GET.get('project_id')
    if not project_id:
        return JsonResponse([], safe=False)
    components = list(Component.objects.filter(project_id=project_id).values('id', 'name'))
    return JsonResponse(components, safe=False)


def my_report_list(request):
    """
    Displays a list of reports created by the logged-in user.
    """
    if not request.user.is_authenticated:
        return redirect('login')

    reports = Report.objects.filter(reported_by=request.user).select_related('project', 'reported_by').distinct()

    return render(request, 'report_list.html', {'reports': reports})


def assigned_to_me(request):
    """
    Displays a list of reports assigned to the logged-in user.
    """
    if not request.user.is_authenticated:
        return redirect('login')

    reports = Report.objects.filter(assigned_to=request.user).select_related('project', 'reported_by').distinct()

    return render(request, 'report_list.html', {'reports': reports})


@login_required
def reassign_report(request, project_pk, report_pk):
    report = get_object_or_404(Report, pk=report_pk, project__pk=project_pk)
    project = report.project

    if not rules.is_project_owner(request.user, project):
        return HttpResponseForbidden("You are not authorized to perform this action.")

    if request.method == 'POST':
        assignee_id = request.POST.get('assignee')
        if assignee_id:
            try:
                assignee = User.objects.get(pk=assignee_id)
                report.assigned_to = assignee
                report.save()
            except User.DoesNotExist:
                pass
    
    return redirect('projects:reports:report_detail', project_pk=project.pk, report_pk=report.pk)


@login_required
def change_report_status(request, project_pk, report_pk):
    report = get_object_or_404(Report, pk=report_pk, project__pk=project_pk)

    if not rules.can_change_status(request.user, report):
        return HttpResponseForbidden("You are not authorized to perform this action.")

    if request.method == 'POST':
        status = request.POST.get('status')
        if status and status in [choice[0] for choice in Report.STATUS_CHOICES]:
            report.status = status
            report.save()
            
    return redirect('projects:reports:report_detail', project_pk=report.project.pk, report_pk=report.pk)

@login_required
def change_report_visibility(request, project_pk, report_pk):
    report = get_object_or_404(Report, pk=report_pk, project__pk=project_pk)

    if not rules.is_project_member(request.user, report.project):
        return HttpResponseForbidden("You are not authorized to perform this action.")

    if request.method == 'POST':
        visibility = request.POST.get('visibility')
        if visibility == 'True':
            report.visibility = True
        else:
            report.visibility = False
        report.save()
            
    return redirect('projects:reports:report_detail', project_pk=report.project.pk, report_pk=report.pk)

@login_required
def change_report_impact(request, project_pk, report_pk):
    report = get_object_or_404(Report, pk=report_pk, project__pk=project_pk)

    if not rules.is_project_member(request.user, report.project):
        return HttpResponseForbidden("You are not authorized to perform this action.")

    if request.method == 'POST':
        impact = request.POST.get('impact')
        if impact and impact in [choice[0] for choice in Report.IMPACT_CHOICES]:
            report.impact = impact
            report.save()
            
    return redirect('projects:reports:report_detail', project_pk=report.project.pk, report_pk=report.pk)