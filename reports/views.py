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
from reports.services import *



# Create your views here.


def report_list(request, project_uuid=None):
    """
    Displays a list of all reports for a specific project.
    """
    # Fetches the project object based on the primary key from the URL.
    project = get_object_or_404(Project, uuid=project_uuid)
    
    if not rules.can_access_project(request.user, project):
        return HttpResponseForbidden("You do not have permission to access this project.")
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

    # Page-specific search
    q = request.GET.get('q', '').strip()
    if q:
        reports = reports.filter(
            Q(title__icontains=q) | Q(description__icontains=q) | Q(component__name__icontains=q)
        ).distinct()

    # Renders the 'report_list.html' template, passing the reports and project as context.
    return render(request, 'report_list.html', {'reports': reports, 'project': project})

def report_detail(request, report_uuid, project_uuid=None):
    """
    Displays the details of a single report, including its comments.
    """
    # Flashes the specific report, ensuring it belongs to the correct project if project_uuid is provided.
    if project_uuid:
        report = get_object_or_404(Report, project__uuid=project_uuid, uuid=report_uuid)
    else:
        report = get_object_or_404(Report, uuid=report_uuid)
    # Gets the project from the report object.
    project = report.project

    if not rules.can_access_project(request.user, project):
        return HttpResponseForbidden("You do not have permission to access this project.")

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
    
    collaborators = report.project.collaborators.all()

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
        'collaborators': collaborators,
        'status_choices': Report.STATUS_CHOICES,
        'impact_choices': Report.IMPACT_CHOICES,
        'can_change_status': user_can_change_status,
        'history': get_report_history(request.user, report),
        })

@login_required
def create_report(request, project_uuid=None):    
    """
    View for creating a new report.
    """
    if not request.user.is_email_verified:
        from accounts.views import render_verification_required
        return render_verification_required(request, "Verify your email to create reports.")

    project = None
    
    if project_uuid is not None:
        project = get_object_or_404(Project, uuid=project_uuid)

    if project and not rules.can_access_project(request.user, project):
        return HttpResponseForbidden("You do not have permission to access this project.")

    if request.method == 'POST':
        form = ReportForm(request.POST, request.FILES, project=project, user=request.user)
        
        if form.is_valid():
            report = form.save(commit=False)
            report.reported_by = request.user
            if project:
                report.project = project
            report.assigned_to = report.project.owner
            report.save()

            from notifications.services import create_notification
            recipients = {report.project.owner, report.project.project_head}
            for recipient in recipients:
                if recipient and recipient != request.user:
                    create_notification(
                        recipient=recipient,
                        actor=request.user,
                        notification_type='report_assigned',  # Using report_assigned as template/type
                        title="New Issue Reported",
                        message=f"A new issue '{report.title}' was reported by {request.user.username} in project '{report.project.title}'.",
                        target_content_type='report',
                        target_uuid=report.uuid
                    )

            return redirect('projects:reports:report_detail', project_uuid=report.project.uuid, report_uuid=report.uuid)
    else:
        form = ReportForm(project=project, user=request.user)
        
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

    # Page-specific search
    q = request.GET.get('q', '').strip()
    if q:
        reports = reports.filter(
            Q(title__icontains=q) | Q(description__icontains=q) | Q(component__name__icontains=q)
        ).distinct()

    reports = reports.order_by('-updated_at')

    return render(request, 'report_list.html', {
        'reports': reports,
        'title': 'My Reports',
        'subtitle': 'Manage issues and reports created by you.'
    })


def assigned_to_me(request):
    """
    Displays a list of reports assigned to the logged-in user.
    """
    if not request.user.is_authenticated:
        return redirect('login')

    reports = Report.objects.filter(assigned_to=request.user).select_related('project', 'reported_by').distinct()

    # Page-specific search
    q = request.GET.get('q', '').strip()
    if q:
        reports = reports.filter(
            Q(title__icontains=q) | Q(description__icontains=q) | Q(component__name__icontains=q)
        ).distinct()

    reports = reports.order_by('-updated_at')

    return render(request, 'report_list.html', {
        'reports': reports,
        'title': 'Assigned to Me',
        'subtitle': 'Manage issues assigned directly to you.'
    })


@login_required
def needs_attention_view(request):
    """
    Displays critical reports assigned to the user or reported on their projects.
    """
    user = request.user
    reports = Report.objects.filter(
        (Q(severity='critical') | Q(impact='critical')) & (
            Q(assigned_to=user) | 
            Q(project__owner=user) | 
            Q(project__project_head=user) | 
            Q(project__collaborators=user)
        )
    ).exclude(
        status__in=['resolved', 'closed']
    ).select_related('project', 'reported_by').distinct()
    
    # Page-specific search
    q = request.GET.get('q', '').strip()
    if q:
        reports = reports.filter(
            Q(title__icontains=q) | Q(description__icontains=q) | Q(component__name__icontains=q)
        ).distinct()
        
    reports = reports.order_by('-updated_at')
    
    return render(request, 'report_list.html', {
        'reports': reports,
        'title': 'Needs Attention',
        'subtitle': 'Critical reports assigned to you or reported on your projects.'
    })


@login_required
def reassign_report(request, project_uuid, report_uuid):
    report = get_object_or_404(Report, uuid=report_uuid, project__uuid=project_uuid)
    project = report.project

    if not rules.is_project_owner(request.user, project):
        return HttpResponseForbidden("You are not authorized to perform this action.")

    assign_report(request=request, report=report, assignee=request.user, actor=request.user)
    
    return redirect('projects:reports:report_detail', project_uuid=project.uuid, report_uuid=report.uuid)


@login_required
def change_report_status(request, project_uuid, report_uuid):
    report = get_object_or_404(Report, uuid=report_uuid, project__uuid=project_uuid)

    if not rules.can_change_status(request.user, report):
        return HttpResponseForbidden("You are not authorized to perform this action.")
    
    if request.method == 'POST':
        status = request.POST.get('status')

    update_report_status(request=request, report=report, new_status=status, actor=request.user)

    return redirect('projects:reports:report_detail', project_uuid=report.project.uuid, report_uuid=report.uuid)

@login_required
def change_report_visibility(request, project_uuid, report_uuid):
    report = get_object_or_404(Report, uuid=report_uuid, project__uuid=project_uuid)

    if not rules.is_project_member(request.user, report.project):
        return HttpResponseForbidden("You are not authorized to perform this action.")

    if request.method == 'POST':
        visibility = request.POST.get('visibility')
        
    update_report_visibility(report=report, new_visibility=(visibility == 'true'), actor=request.user)
            
    return redirect('projects:reports:report_detail', project_uuid=report.project.uuid, report_uuid=report.uuid)

@login_required
def change_report_impact(request, project_uuid, report_uuid):
    report = get_object_or_404(Report, uuid=report_uuid, project__uuid=project_uuid)

    if not rules.is_project_member(request.user, report.project):
        return HttpResponseForbidden("You are not authorized to perform this action.")

    if request.method == 'POST':
        impact = request.POST.get('impact')

    update_report_impact(report=report, new_impact=impact, actor=request.user)
            
    return redirect('projects:reports:report_detail', project_uuid=report.project.uuid, report_uuid=report.uuid)