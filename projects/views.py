import logging
from django.shortcuts import render, redirect, get_object_or_404
from .forms import ProjectForm, ComponentFormSet, ComponentForm, ComponentFormSet
from django.contrib.auth.decorators import login_required
from projects.models import Project
from django.http import HttpResponseForbidden
from accounts.models import User
from django.db.models import Q, Count
from projects.services import update_project, get_project_history, get_component_changes_for_project_log
import rules.views as rules
from organisations.models import Organisation


logger = logging.getLogger(__name__)

# Create your views here.


@login_required
def register_project(request):
    if not request.user.is_email_verified:
        from accounts.views import render_verification_required
        return render_verification_required(request, "Verify your email to create projects.")

    if request.method == "POST":
        project_form = ProjectForm(request.POST, user=request.user)
        component_formset = ComponentFormSet(request.POST, instance=Project(), prefix='components')

        collaborators_emails = request.POST.get('collaborators', '')

        if project_form.is_valid() and component_formset.is_valid():
            from django.db import transaction
            with transaction.atomic():
                project = project_form.save(commit=False)
                # Fallback to current user if owner not set
                if not getattr(project, 'owner', None):
                    project.owner = request.user
                
                # Check org-owned constraints via URL parameter just in case
                org_uuid = request.GET.get('org')
                if org_uuid:
                    try:
                        org = Organisation.objects.get(uuid=org_uuid)
                        if rules.is_organisation_owner(request.user, org):
                            project.org = org
                    except Organisation.DoesNotExist:
                        pass
                
                project.save()
                project_form._save_project_head_invite(project)
                project.collaborators.add(project.owner)
                if request.user != project.owner:
                    project.collaborators.add(request.user)

                if collaborators_emails:
                    emails = [email.strip() for email in collaborators_emails.split(',')]
                    from notifications.services import create_invitation
                    for email in emails:
                        user = User.objects.filter(email=email).first()
                        if user and user != request.user and user != project.owner:
                            try:
                                create_invitation(
                                    invite_type='collaborator',
                                    invited_by=request.user,
                                    invited_user=user,
                                    project=project
                                )
                            except PermissionError as e:
                                messages.warning(request, str(e))

                # Bind component formset to the saved project and save
                component_formset.instance = project
                component_formset.save()

                return redirect("projects:projects_view")
        # If we get here, either form has errors — fall through to render with errors shown
    else:
        project_form = ProjectForm(user=request.user)
        org_uuid = request.GET.get('org')
        if org_uuid:
            try:
                org = Organisation.objects.get(uuid=org_uuid)
                if rules.is_organisation_owner(request.user, org):
                    project_form.initial['org'] = org
            except Organisation.DoesNotExist:
                pass
        component_formset = ComponentFormSet(instance=Project(), prefix='components')
    
    # Preserve collaborators field value for re-render
    collaborator_emails = request.POST.get('collaborators', '') if request.method == 'POST' else ''

    return render(request, 'register_project.html', {
        'form': project_form,
        'component_formset': component_formset,
        'collaborator_emails': collaborator_emails,
    })



def apply_project_filters_and_sorting(projects_qs, request):
    # 1. On-page Search
    q = request.GET.get('q', '').strip()
    if q:
        projects_qs = projects_qs.filter(
            Q(title__icontains=q) | Q(description__icontains=q) | Q(owner__username__icontains=q)
        ).distinct()

    # 2. Filters
    visibility = request.GET.get('visibility', '').strip()
    if visibility:
        projects_qs = projects_qs.filter(visibility=visibility)

    org_id = request.GET.get('org_id', '').strip()
    if org_id:
        projects_qs = projects_qs.filter(org_id=org_id)

    # 3. Sorting
    sort_by = request.GET.get('sort_by', '').strip()
    if sort_by == 'title_asc':
        projects_qs = projects_qs.order_by('title')
    elif sort_by == 'title_desc':
        projects_qs = projects_qs.order_by('-title')
    elif sort_by == 'oldest':
        projects_qs = projects_qs.order_by('created_at')
    elif sort_by == 'newest':
        projects_qs = projects_qs.order_by('-created_at')
    else:
        # Default recently updated
        projects_qs = projects_qs.order_by('-updated_at')

    return projects_qs


@login_required
def projects_view(request):
    projects = Project.objects.filter(public=True).select_related('org', 'owner').annotate(num_components=Count('project_components'))
    projects = apply_project_filters_and_sorting(projects, request)

    # H-03: Scope org filter to user's own orgs only — don't expose all org names
    if request.user.is_authenticated:
        from organisations.services import get_user_organisations
        filter_orgs = get_user_organisations(request.user).order_by('name')
    else:
        filter_orgs = Organisation.objects.none()

    context = {
        'projects': projects,
        'filter_orgs': filter_orgs,
        'selected_visibility': request.GET.get('visibility', ''),
        'selected_org_id': int(request.GET.get('org_id', '')) if request.GET.get('org_id', '').isdigit() else '',
        'selected_sort_by': request.GET.get('sort_by', ''),
        'q': request.GET.get('q', '').strip(),
    }

    if request.headers.get('HX-Request') or request.GET.get('hx_request') == 'true':
        return render(request, 'projects/partials/projects_grid_partial.html', context)

    return render(request, 'projects_view.html', context)



def _get_public_link(project):
    """Lazily create and return the PublicReportingLink for a project."""
    from public_portal.services import get_or_create_link
    return get_or_create_link(project)


@login_required
def project_detail(request, project_uuid):
    user = request.user
    # C-05: Use get_object_or_404 instead of .get() to return clean 404 on invalid UUID
    project = get_object_or_404(Project.objects.select_related('org', 'owner', 'project_head'), uuid=project_uuid)
    
    # Enforce access scoping
    if not rules.can_access_project(user, project):
        return HttpResponseForbidden("You do not have permission to view this project.")
        
    is_owner = user.is_authenticated and rules.is_project_owner(user, project)
    is_member = user.is_authenticated and rules.is_project_member(user, project)

    # Calculate Statistics
    from reports.models import Report
    reports_qs = Report.objects.filter(project=project)
    total_reports = reports_qs.count()
    open_reports = reports_qs.filter(status__in=['open', 'in_progress']).count()
    resolved_reports = reports_qs.filter(status='resolved').count()
    closed_reports = reports_qs.filter(status='closed').count()
    critical_reports = reports_qs.filter(severity__in=['high', 'critical']).count()

    # Average Resolution Time
    from django.db.models import Avg, F, ExpressionWrapper, DurationField
    avg_duration = reports_qs.filter(
        status__in=['resolved', 'closed'],
        updated_at__gt=F('created_at')
    ).aggregate(
        avg_time=Avg(ExpressionWrapper(F('updated_at') - F('created_at'), output_field=DurationField()))
    )['avg_time']

    avg_resolution_time = "N/A"
    if avg_duration is not None:
        avg_seconds = avg_duration.total_seconds()
        if avg_seconds < 3600:
            avg_resolution_time = f"{int(avg_seconds / 60)}m"
        elif avg_seconds < 86400:
            avg_resolution_time = f"{round(avg_seconds / 3600, 1)}h"
        else:
            avg_resolution_time = f"{round(avg_seconds / 86400, 1)}d"

    # Project Health Summary
    health_score = 100
    health_rating = "Healthy"
    if total_reports > 0:
        resolved_ratio = (resolved_reports + closed_reports) / total_reports
        health_score = int(resolved_ratio * 100)
        open_critical = reports_qs.filter(status__in=['open', 'in_progress'], severity__in=['high', 'critical']).count()
        if open_critical > 3 or (total_reports >= 10 and resolved_ratio < 0.3):
            health_rating = "Critical"
        elif open_critical > 0 or (total_reports >= 5 and resolved_ratio < 0.6):
            health_rating = "Warning"
        else:
            health_rating = "Healthy"

    # Recent Reports
    recent_reports = reports_qs.select_related('reported_by', 'component').order_by('-created_at')[:5]    # Tasks Checklist
    active_tasks = project.tasks.filter(is_completed=False).order_by('-created_at')
    completed_tasks = project.tasks.filter(is_completed=True).order_by('-created_at')

    # Unified Activities history
    from audit.models import AuditLog
    report_uuids = [str(u) for u in reports_qs.values_list('uuid', flat=True)]
    activities = AuditLog.objects.filter(
        (Q(entity_type="Project") & Q(entity_id=str(project.uuid))) |
        (Q(parent_type="Project") & Q(parent_id=str(project.id))) |
        (Q(entity_type="Report") & Q(entity_id__in=report_uuids))
    ).select_related('actor').order_by('-created_at')[:10]
    
    enriched_history = []
    for log in activities:
        # If it's collaborators, format IDs/UUIDs into emails if they are list/UUID strings
        if log.field_name == 'collaborators':
            def parse_collaborator_string(val_str):
                if not val_str:
                    return ""
                if '@' in val_str and '[' not in val_str:
                    return val_str
                
                import ast
                import re
                try:
                    cleaned = re.sub(r"UUID\('([^']+)'\)", r"'\1'", val_str)
                    parsed = ast.literal_eval(cleaned)
                    if isinstance(parsed, (list, tuple, set)):
                        emails = []
                        for item in parsed:
                            user = None
                            if isinstance(item, int):
                                user = User.objects.filter(id=item).first()
                            elif isinstance(item, str):
                                if item.isdigit():
                                    user = User.objects.filter(id=int(item)).first()
                                else:
                                    try:
                                        user = User.objects.filter(uuid=item).first()
                                    except Exception:
                                        pass
                            if user:
                                emails.append(user.email)
                            else:
                                emails.append(str(item))
                        return ", ".join(emails)
                except Exception:
                    pass
                return val_str

            log.old_value = parse_collaborator_string(log.old_value)
            log.new_value = parse_collaborator_string(log.new_value)

        elif log.field_name == 'visibility':
            visibility_map = {
                'public': 'Public',
                'org': 'Organization Members Only',
                'private': 'Private (Owner & Collaborators Only)'
            }
            if log.old_value in visibility_map:
                log.old_value = visibility_map[log.old_value]
            if log.new_value in visibility_map:
                log.new_value = visibility_map[log.new_value]

        elif log.field_name == 'org':
            def resolve_org_name(val_str):
                if not val_str or val_str == 'None':
                    return "None"
                if not val_str.isdigit():
                    try:
                        from uuid import UUID
                        UUID(val_str)
                        org = Organisation.objects.filter(uuid=val_str).first()
                        if org:
                            return org.name
                    except Exception:
                        return val_str
                else:
                    org = Organisation.objects.filter(id=int(val_str)).first()
                    if org:
                        return org.name
                return val_str

            log.old_value = resolve_org_name(log.old_value)
            log.new_value = resolve_org_name(log.new_value)

        elif log.field_name == 'project_head':
            def resolve_user_email(val_str):
                if not val_str or val_str == 'None':
                    return "None"
                if '@' in val_str:
                    return val_str
                if val_str.isdigit():
                    user = User.objects.filter(id=int(val_str)).first()
                else:
                    try:
                        user = User.objects.filter(uuid=val_str).first()
                    except Exception:
                        user = None
                return user.email if user else val_str

            log.old_value = resolve_user_email(log.old_value)
            log.new_value = resolve_user_email(log.new_value)

        log_dict = {
            'log': log,
            'component_changes': None
        }
        if log.field_name == 'components':
            log_dict['component_changes'] = get_component_changes_for_project_log(project.id, log)
        enriched_history.append(log_dict)
    
    # Filtered collaborators to avoid listing owner/project_head twice
    exclude_ids = [project.owner.id]
    if project.project_head:
        exclude_ids.append(project.project_head.id)
    collaborators_list = project.collaborators.exclude(id__in=exclude_ids)

    return render(request, 'project_details.html', {
        'project': project,
        'is_owner': is_owner,
        'is_member': is_member,
        'collaborators': collaborators_list,
        'total_reports': total_reports,
        'open_reports': open_reports,
        'resolved_reports': resolved_reports,
        'closed_reports': closed_reports,
        'critical_reports': critical_reports,
        'avg_resolution_time': avg_resolution_time,
        'health_score': health_score,
        'health_rating': health_rating,
        'recent_reports': recent_reports,
        'active_tasks': active_tasks,
        'completed_tasks': completed_tasks,
        'history': enriched_history,
        # Public portal link (auto-created on first visit if owner)
        'public_link': _get_public_link(project) if is_owner else None,
    })


@login_required
def edit_project(request, project_uuid):
    project = Project.objects.get(uuid=project_uuid)

    if not rules.is_project_owner(request.user, project):
        return HttpResponseForbidden("You do not have permission to edit this project.")

    if request.method == "POST":
        project_form = ProjectForm(request.POST, instance=project, user=request.user)
        component_formset = ComponentFormSet(
            request.POST, instance=project, prefix="components"
        )

        if project_form.is_valid() and component_formset.is_valid():
            update_project(
                project=project,
                form=project_form,
                component_formset=component_formset,
                collaborator_emails=request.POST.get("collaborators", ""),
                actor=request.user,
            )
            return redirect("projects:project_detail", project_uuid=project.uuid)

    else:
        project_form = ProjectForm(instance=project, user=request.user)
        component_formset = ComponentFormSet(instance=project, prefix="components")

    collaborator_email_list = [
        user.email for user in project.collaborators.all()
        if user != request.user
    ]

    return render(request, "edit_project.html", {
        "form": project_form,
        "component_formset": component_formset,
        "project": project,
        "collaborator_email_list": collaborator_email_list,
        "collaborator_emails": ", ".join(collaborator_email_list),
    })


@login_required
def my_projects_view(request):
    projects = Project.objects.filter(
        Q(org__isnull=True, owner=request.user) |
        Q(org__isnull=False, org__owner=request.user) |
        Q(org__isnull=False, project_head=request.user)
    ).annotate(num_components=Count('project_components')).distinct()
    
    projects = apply_project_filters_and_sorting(projects, request)
    filter_orgs = Organisation.objects.all().order_by('name')

    context = {
        'projects': projects,
        'filter_orgs': filter_orgs,
        'title': 'My Projects',
        'subtitle': 'Manage projects owned by you.',
        'selected_visibility': request.GET.get('visibility', ''),
        'selected_org_id': int(request.GET.get('org_id', '')) if request.GET.get('org_id', '').isdigit() else '',
        'selected_sort_by': request.GET.get('sort_by', ''),
        'q': request.GET.get('q', '').strip(),
    }

    if request.headers.get('HX-Request') or request.GET.get('hx_request') == 'true':
        return render(request, 'projects/partials/projects_grid_partial.html', context)

    return render(request, 'projects_view.html', context)


@login_required
def collaborating_projects_view(request):
    projects = Project.objects.filter(collaborators=request.user).exclude(
        Q(org__isnull=True, owner=request.user) |
        Q(org__isnull=False, org__owner=request.user) |
        Q(org__isnull=False, project_head=request.user)
    ).annotate(num_components=Count('project_components')).distinct()
    
    projects = apply_project_filters_and_sorting(projects, request)
    filter_orgs = Organisation.objects.all().order_by('name')

    context = {
        'projects': projects,
        'filter_orgs': filter_orgs,
        'title': 'Collaborating Projects',
        'subtitle': 'Projects you are collaborating on.',
        'selected_visibility': request.GET.get('visibility', ''),
        'selected_org_id': int(request.GET.get('org_id', '')) if request.GET.get('org_id', '').isdigit() else '',
        'selected_sort_by': request.GET.get('sort_by', ''),
        'q': request.GET.get('q', '').strip(),
    }

    if request.headers.get('HX-Request') or request.GET.get('hx_request') == 'true':
        return render(request, 'projects/partials/projects_grid_partial.html', context)

    return render(request, 'projects_view.html', context)


@login_required
def add_project_task(request, project_uuid):
    project = get_object_or_404(Project, uuid=project_uuid)
    if not rules.is_project_member(request.user, project):
        return HttpResponseForbidden("Forbidden")
    
    title = request.POST.get('title', '').strip()
    if title:
        from projects.models import ProjectTask
        ProjectTask.objects.create(project=project, title=title)
        
    active_tasks = project.tasks.filter(is_completed=False).order_by('-created_at')
    completed_tasks = project.tasks.filter(is_completed=True).order_by('-created_at')
    return render(request, 'projects/partials/tasks_partial.html', {
        'project': project, 
        'active_tasks': active_tasks,
        'completed_tasks': completed_tasks
    })


@login_required
def toggle_project_task(request, project_uuid, task_id):
    project = get_object_or_404(Project, uuid=project_uuid)
    if not rules.is_project_member(request.user, project):
        return HttpResponseForbidden("Forbidden")
        
    from projects.models import ProjectTask
    task = get_object_or_404(ProjectTask, id=task_id, project=project)
    
    # Check if request comes from checkbox toggle via csrf post
    task.is_completed = not task.is_completed
    task.save()
    
    active_tasks = project.tasks.filter(is_completed=False).order_by('-created_at')
    completed_tasks = project.tasks.filter(is_completed=True).order_by('-created_at')
    return render(request, 'projects/partials/tasks_partial.html', {
        'project': project, 
        'active_tasks': active_tasks,
        'completed_tasks': completed_tasks
    })


@login_required
def delete_project_task(request, project_uuid, task_id):
    project = get_object_or_404(Project, uuid=project_uuid)
    if not rules.is_project_member(request.user, project):
        return HttpResponseForbidden("Forbidden")
        
    from projects.models import ProjectTask
    task = get_object_or_404(ProjectTask, id=task_id, project=project)
    task.delete()
    
    active_tasks = project.tasks.filter(is_completed=False).order_by('-created_at')
    completed_tasks = project.tasks.filter(is_completed=True).order_by('-created_at')
    return render(request, 'projects/partials/tasks_partial.html', {
        'project': project, 
        'active_tasks': active_tasks,
        'completed_tasks': completed_tasks
    })
