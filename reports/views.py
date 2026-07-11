from django.shortcuts import render, redirect, get_object_or_404
from reports.forms import ReportForm
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden, HttpResponse
from django.contrib import messages
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


def apply_report_filters_and_sorting(reports_qs, request):
    # 1. On-page Search
    q = request.GET.get('q', '').strip()
    if q:
        reports_qs = reports_qs.filter(
            Q(title__icontains=q) | Q(description__icontains=q) | Q(component__name__icontains=q)
        ).distinct()

    # 2. Filters
    status = request.GET.get('status', '').strip()
    if status:
        reports_qs = reports_qs.filter(status=status)

    impact = request.GET.get('impact', '').strip()
    if impact:
        reports_qs = reports_qs.filter(impact=impact)

    assignee_id = request.GET.get('assignee_id', '').strip()
    if assignee_id:
        reports_qs = reports_qs.filter(assigned_to_id=assignee_id)

    reporter_id = request.GET.get('reporter_id', '').strip()
    if reporter_id:
        reports_qs = reports_qs.filter(reported_by_id=reporter_id)

    component_id = request.GET.get('component_id', '').strip()
    if component_id:
        reports_qs = reports_qs.filter(component_id=component_id)

    date_start = request.GET.get('date_start', '').strip()
    if date_start:
        reports_qs = reports_qs.filter(created_at__date__gte=date_start)

    date_end = request.GET.get('date_end', '').strip()
    if date_end:
        reports_qs = reports_qs.filter(created_at__date__lte=date_end)

    # 3. Sorting
    sort_by = request.GET.get('sort_by', '').strip()
    if sort_by == 'oldest':
        reports_qs = reports_qs.order_by('created_at')
    elif sort_by == 'title_asc':
        reports_qs = reports_qs.order_by('title')
    elif sort_by == 'title_desc':
        reports_qs = reports_qs.order_by('-title')
    elif sort_by == 'severity_desc':
        from django.db.models import Case, When, Value, IntegerField
        reports_qs = reports_qs.annotate(
            severity_weight=Case(
                When(impact='critical', then=Value(4)),
                When(impact='high', then=Value(3)),
                When(impact='medium', then=Value(2)),
                When(impact='low', then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            )
        ).order_by('-severity_weight', '-updated_at')
    elif sort_by == 'status':
        reports_qs = reports_qs.order_by('status', '-updated_at')
    else:
        # Default sort: newest
        reports_qs = reports_qs.order_by('-updated_at')

    return reports_qs


def report_list(request, project_uuid=None):
    """
    Displays a list of all reports for a specific project.
    """
    project = get_object_or_404(Project, uuid=project_uuid)
    
    if not rules.can_access_project(request.user, project):
        return HttpResponseForbidden("You do not have permission to access this project.")

    base_qs = Report.objects.filter(project=project).select_related('reported_by', 'project', 'component').distinct()

    if request.user.is_authenticated:
        if rules.is_project_owner(request.user, project) or rules.is_project_member(request.user, project):
            reports = base_qs
        else:
            reports = base_qs.filter(Q(visibility=True) | Q(reported_by=request.user))
    else:
        reports = base_qs.filter(visibility=True)

    reports = apply_report_filters_and_sorting(reports, request)

    # Context choices
    filter_users = User.objects.all().order_by('username')
    filter_components = Component.objects.filter(project=project).order_by('name')

    context = {
        'reports': reports,
        'project': project,
        'filter_users': filter_users,
        'filter_components': filter_components,
        'selected_status': request.GET.get('status', ''),
        'selected_impact': request.GET.get('impact', ''),
        'selected_assignee_id': int(request.GET.get('assignee_id', '')) if request.GET.get('assignee_id', '').isdigit() else '',
        'selected_reporter_id': int(request.GET.get('reporter_id', '')) if request.GET.get('reporter_id', '').isdigit() else '',
        'selected_component_id': int(request.GET.get('component_id', '')) if request.GET.get('component_id', '').isdigit() else '',
        'selected_date_start': request.GET.get('date_start', ''),
        'selected_date_end': request.GET.get('date_end', ''),
        'selected_sort_by': request.GET.get('sort_by', ''),
        'q': request.GET.get('q', '').strip(),
    }

    if request.headers.get('HX-Request') or request.GET.get('hx_request') == 'true':
        return render(request, 'reports/partials/reports_list_partial.html', context)

    return render(request, 'report_list.html', context)

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

    # Track recently viewed in session
    recently_viewed = request.session.get('recently_viewed_reports', [])
    report_uuid_str = str(report.uuid)
    if report_uuid_str in recently_viewed:
        recently_viewed.remove(report_uuid_str)
    recently_viewed.insert(0, report_uuid_str)
    request.session['recently_viewed_reports'] = recently_viewed[:5]
    request.session.modified = True

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
    
    # Check if report is bookmarked or followed
    is_bookmarked = False
    is_watching = False
    can_edit = False
    can_delete = False
    if request.user.is_authenticated:
        from reports.models import ReportBookmark, ReportFollower
        is_bookmarked = ReportBookmark.objects.filter(user=request.user, report=report).exists()
        is_watching = ReportFollower.objects.filter(user=request.user, report=report).exists()
        can_edit = rules.can_edit_report(request.user, report)
        can_delete = rules.can_delete_report(request.user, report)

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
        'is_bookmarked': is_bookmarked,
        'is_watching': is_watching,
        'can_edit': can_edit,
        'can_delete': can_delete,
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
        # Resolve project if scenario 2 (selected from select dropdown)
        if not project:
            project_id = request.POST.get('project')
            if project_id:
                try:
                    project = Project.objects.get(id=project_id)
                except Project.DoesNotExist:
                    pass

        form = ReportForm(request.POST, request.FILES, project=project, user=request.user)
        files = request.FILES.getlist('attachments')

        # Backend validations for multiple attachments
        if project:
            if len(files) > project.max_attachments:
                form.add_error(None, f"A maximum of {project.max_attachments} attachments are allowed for reports in this project.")
            
            allowed_types = [ext.strip().lower() for ext in project.allowed_attachment_types.split(',') if ext.strip()]
            for f in files:
                ext = '.' + f.name.split('.')[-1].lower() if '.' in f.name else ''
                if ext not in allowed_types:
                    form.add_error(None, f"File type '{ext}' of file '{f.name}' is not allowed. Allowed types: {project.allowed_attachment_types}")
                    break
        
        if form.is_valid():
            report = form.save(commit=False)
            report.reported_by = request.user
            if project:
                report.project = project
            report.assigned_to = report.project.owner
            report.save()

            # Save multiple attachments
            from reports.models import ReportAttachment
            for f in files:
                ReportAttachment.objects.create(
                    report=report,
                    file=f,
                    filename=f.name,
                    file_size=f.size
                )

            from notifications.services import create_notification
            recipients = {report.project.owner, report.project.project_head}
            for recipient in recipients:
                if recipient and recipient != request.user:
                    create_notification(
                        recipient=recipient,
                        actor=request.user,
                        notification_type='report_assigned',
                        title="New Issue Reported",
                        message=f"A new issue '{report.title}' was reported by {request.user.username} in project '{report.project.title}'.",
                        target_content_type='report',
                        target_uuid=report.uuid
                    )

            return redirect('projects:reports:report_detail', project_uuid=report.project.uuid, report_uuid=report.uuid)
    else:
        form = ReportForm(project=project, user=request.user)
        
    return render(request, 'create_report.html', {'form': form, 'project': project})


@login_required
def get_components(request):
    project_id = request.GET.get('project_id')
    if not project_id:
        return JsonResponse([], safe=False)
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return JsonResponse([], safe=False)
    if not rules.can_access_project(request.user, project):
        return JsonResponse([], safe=False)
    components = list(Component.objects.filter(project_id=project_id).values('id', 'name'))
    return JsonResponse(components, safe=False)


@login_required
def get_project_config(request):
    project_id = request.GET.get('project_id')
    if not project_id:
        return JsonResponse({}, safe=False)
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return JsonResponse({}, safe=False)
    if not rules.can_access_project(request.user, project):
        return JsonResponse({}, safe=False)
    return JsonResponse({
        'max_attachments': project.max_attachments,
        'allowed_attachment_types': project.allowed_attachment_types
    })


@login_required
def my_report_list(request):
    """
    Displays a list of reports created by the logged-in user.
    """

    reports = Report.objects.filter(reported_by=request.user).select_related('project', 'reported_by', 'component').distinct()
    reports = apply_report_filters_and_sorting(reports, request)

    # Context choices
    filter_users = User.objects.all().order_by('username')
    filter_components = Component.objects.all().order_by('name')

    context = {
        'reports': reports,
        'title': 'My Reports',
        'subtitle': 'Manage issues and reports created by you.',
        'filter_users': filter_users,
        'filter_components': filter_components,
        'selected_status': request.GET.get('status', ''),
        'selected_impact': request.GET.get('impact', ''),
        'selected_assignee_id': int(request.GET.get('assignee_id', '')) if request.GET.get('assignee_id', '').isdigit() else '',
        'selected_reporter_id': int(request.GET.get('reporter_id', '')) if request.GET.get('reporter_id', '').isdigit() else '',
        'selected_component_id': int(request.GET.get('component_id', '')) if request.GET.get('component_id', '').isdigit() else '',
        'selected_date_start': request.GET.get('date_start', ''),
        'selected_date_end': request.GET.get('date_end', ''),
        'selected_sort_by': request.GET.get('sort_by', ''),
        'q': request.GET.get('q', '').strip(),
    }

    if request.headers.get('HX-Request') or request.GET.get('hx_request') == 'true':
        return render(request, 'reports/partials/reports_list_partial.html', context)

    return render(request, 'report_list.html', context)


@login_required
def assigned_to_me(request):
    """
    Displays a list of reports assigned to the logged-in user.
    """

    reports = Report.objects.filter(assigned_to=request.user).select_related('project', 'reported_by', 'component').distinct()
    reports = apply_report_filters_and_sorting(reports, request)

    # Context choices
    filter_users = User.objects.all().order_by('username')
    filter_components = Component.objects.all().order_by('name')

    context = {
        'reports': reports,
        'title': 'Assigned to Me',
        'subtitle': 'Manage issues assigned directly to you.',
        'filter_users': filter_users,
        'filter_components': filter_components,
        'selected_status': request.GET.get('status', ''),
        'selected_impact': request.GET.get('impact', ''),
        'selected_assignee_id': int(request.GET.get('assignee_id', '')) if request.GET.get('assignee_id', '').isdigit() else '',
        'selected_reporter_id': int(request.GET.get('reporter_id', '')) if request.GET.get('reporter_id', '').isdigit() else '',
        'selected_component_id': int(request.GET.get('component_id', '')) if request.GET.get('component_id', '').isdigit() else '',
        'selected_date_start': request.GET.get('date_start', ''),
        'selected_date_end': request.GET.get('date_end', ''),
        'selected_sort_by': request.GET.get('sort_by', ''),
        'q': request.GET.get('q', '').strip(),
    }

    if request.headers.get('HX-Request') or request.GET.get('hx_request') == 'true':
        return render(request, 'reports/partials/reports_list_partial.html', context)

    return render(request, 'report_list.html', context)


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
    ).select_related('project', 'reported_by', 'component').distinct()
    
    reports = apply_report_filters_and_sorting(reports, request)

    # Context choices
    filter_users = User.objects.all().order_by('username')
    filter_components = Component.objects.all().order_by('name')

    context = {
        'reports': reports,
        'title': 'Needs Attention',
        'subtitle': 'Critical reports assigned to you or reported on your projects.',
        'filter_users': filter_users,
        'filter_components': filter_components,
        'selected_status': request.GET.get('status', ''),
        'selected_impact': request.GET.get('impact', ''),
        'selected_assignee_id': int(request.GET.get('assignee_id', '')) if request.GET.get('assignee_id', '').isdigit() else '',
        'selected_reporter_id': int(request.GET.get('reporter_id', '')) if request.GET.get('reporter_id', '').isdigit() else '',
        'selected_component_id': int(request.GET.get('component_id', '')) if request.GET.get('component_id', '').isdigit() else '',
        'selected_date_start': request.GET.get('date_start', ''),
        'selected_date_end': request.GET.get('date_end', ''),
        'selected_sort_by': request.GET.get('sort_by', ''),
        'q': request.GET.get('q', '').strip(),
    }

    if request.headers.get('HX-Request') or request.GET.get('hx_request') == 'true':
        return render(request, 'reports/partials/reports_list_partial.html', context)

    return render(request, 'report_list.html', context)


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


@login_required
def edit_report(request, report_uuid, project_uuid=None):
    if project_uuid:
        report = get_object_or_404(Report, project__uuid=project_uuid, uuid=report_uuid)
    else:
        report = get_object_or_404(Report, uuid=report_uuid)
    
    project = report.project
    
    if not rules.can_edit_report(request.user, report):
        return HttpResponseForbidden("You do not have permission to edit this report.")
    
    if request.method == 'POST':
        form = ReportForm(request.POST, request.FILES, instance=report, project=project, user=request.user)
        files = request.FILES.getlist('attachments')

        # Backend validations for multiple attachments
        existing_count = report.attachments.count()
        if len(files) + existing_count > project.max_attachments:
            form.add_error(None, f"A maximum of {project.max_attachments} attachments are allowed for reports in this project. (This report already has {existing_count} attachments).")
        
        allowed_types = [ext.strip().lower() for ext in project.allowed_attachment_types.split(',') if ext.strip()]
        for f in files:
            ext = '.' + f.name.split('.')[-1].lower() if '.' in f.name else ''
            if ext not in allowed_types:
                form.add_error(None, f"File type '{ext}' of file '{f.name}' is not allowed. Allowed types: {project.allowed_attachment_types}")
                break

        if form.is_valid():
            form.save()

            # Save new attachments
            from reports.models import ReportAttachment
            for f in files:
                ReportAttachment.objects.create(
                    report=report,
                    file=f,
                    filename=f.name,
                    file_size=f.size
                )

            messages.success(request, "Report updated successfully.")
            return redirect('projects:reports:report_detail', project_uuid=project.uuid, report_uuid=report.uuid)
    else:
        form = ReportForm(instance=report, project=project, user=request.user)
        
    return render(request, 'edit_report.html', {
        'form': form,
        'project': project,
        'report': report,
        'existing_attachments': report.attachments.all()
    })


@login_required
def delete_report(request, report_uuid, project_uuid=None):
    if project_uuid:
        report = get_object_or_404(Report, project__uuid=project_uuid, uuid=report_uuid)
    else:
        report = get_object_or_404(Report, uuid=report_uuid)
        
    project = report.project
    
    if not rules.can_delete_report(request.user, report):
        return HttpResponseForbidden("You do not have permission to delete this report.")
        
    if request.method == 'POST':
        report.delete()
        messages.success(request, "Report deleted successfully.")
        return redirect('projects:project_detail', project_uuid=project.uuid)
        
    return render(request, 'reports/partials/delete_confirm_modal.html', {'report': report, 'project': project})


@login_required
def toggle_bookmark(request, report_uuid):
    report = get_object_or_404(Report, uuid=report_uuid)
    if not rules.can_access_project(request.user, report.project):
        return HttpResponseForbidden()
        
    from reports.services import toggle_report_bookmark
    is_bookmarked = toggle_report_bookmark(user=request.user, report=report)
    return render(request, 'reports/partials/bookmark_button.html', {
        'report': report,
        'is_bookmarked': is_bookmarked
    })


@login_required
def toggle_watch(request, report_uuid):
    report = get_object_or_404(Report, uuid=report_uuid)
    if not rules.can_access_project(request.user, report.project):
        return HttpResponseForbidden()
        
    from reports.services import toggle_report_follower
    is_watching = toggle_report_follower(user=request.user, report=report)
    return render(request, 'reports/partials/watch_button.html', {
        'report': report,
        'is_watching': is_watching
    })


@login_required
def ajax_check_duplicate(request):
    title = request.GET.get('title', '').strip()
    project_uuid = request.GET.get('project_uuid', '').strip()
    project_id = request.GET.get('project', '').strip()
    report_uuid = request.GET.get('report_uuid', '').strip()
    
    if len(title) < 3:
        return HttpResponse("")
        
    similar_reports = Report.objects.all()
    
    if project_uuid:
        similar_reports = similar_reports.filter(project__uuid=project_uuid)
    elif project_id:
        similar_reports = similar_reports.filter(project__id=project_id)
    else:
        return HttpResponse("")
        
    if report_uuid:
        similar_reports = similar_reports.exclude(uuid=report_uuid)
        
    similar_reports = similar_reports.filter(title__icontains=title).distinct()[:5]
    
    if not similar_reports.exists():
        return HttpResponse("")
        
    return render(request, 'reports/partials/duplicate_check.html', {
        'similar_reports': similar_reports
    })


@login_required
def delete_attachment(request, attachment_id, project_uuid=None):
    from reports.models import ReportAttachment
    attachment = get_object_or_404(ReportAttachment, id=attachment_id)
    report = attachment.report
    
    # Check edit permissions (only the reporter is authorized to change/edit reports)
    if not rules.can_edit_report(request.user, report):
        return HttpResponseForbidden("You do not have permission to delete this attachment.")
        
    attachment.file.delete()
    attachment.delete()
    return HttpResponse("")


@login_required
def bookmarks_and_watches(request):
    from reports.models import ReportBookmark, ReportFollower
    bookmarks = ReportBookmark.objects.filter(user=request.user).select_related('report', 'report__project')
    watches = ReportFollower.objects.filter(user=request.user).select_related('report', 'report__project')
    
    bookmarked_reports = [b.report for b in bookmarks]
    watched_reports = [w.report for w in watches]
    
    return render(request, 'reports/bookmarks_and_watches.html', {
        'bookmarked_reports': bookmarked_reports,
        'watched_reports': watched_reports
    })


@login_required
def save_search(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        query = request.POST.get('q', '').strip()

        # Extract filters
        filters = {
            'status': request.POST.get('status', ''),
            'impact': request.POST.get('impact', ''),
            'assignee_id': request.POST.get('assignee_id', ''),
            'reporter_id': request.POST.get('reporter_id', ''),
            'org_id': request.POST.get('org_id', ''),
            'component_id': request.POST.get('component_id', ''),
            'date_start': request.POST.get('date_start', ''),
            'date_end': request.POST.get('date_end', ''),
        }
        # Clean empty values
        filters = {k: v for k, v in filters.items() if v}

        if name:
            from reports.models import SavedSearch
            SavedSearch.objects.create(
                user=request.user,
                name=name,
                query=query,
                filters=filters
            )
            messages.success(request, f"Search '{name}' saved successfully.")
        else:
            messages.error(request, "Please enter a name for the saved search.")
    return redirect(request.META.get('HTTP_REFERER', 'global_search'))


@login_required
def delete_saved_search(request, search_id):
    from reports.models import SavedSearch
    saved_search = get_object_or_404(SavedSearch, id=search_id, user=request.user)
    if request.method == 'POST':
        saved_search.delete()
        messages.success(request, "Saved search deleted.")
    return redirect(request.META.get('HTTP_REFERER', 'global_search'))