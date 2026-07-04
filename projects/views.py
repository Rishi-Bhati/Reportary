import logging
from django.shortcuts import render, redirect
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
                project.collaborators.add(project.owner)
                if request.user != project.owner:
                    project.collaborators.add(request.user)

                if collaborators_emails:
                    emails = [email.strip() for email in collaborators_emails.split(',')]
                    for email in emails:
                        user = User.objects.filter(email=email).first()
                        if user:
                            project.collaborators.add(user)

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



def projects_view(request):
    projects = Project.objects.filter(public=True).select_related('org', 'owner').annotate(num_components=Count('project_components'))

    # Page-specific search
    q = request.GET.get('q', '').strip()
    if q:
        projects = projects.filter(
            Q(title__icontains=q) | Q(description__icontains=q) | Q(owner__username__icontains=q)
        ).distinct()

    return render(request, 'projects_view.html', {'projects': projects})



def project_detail(request, project_uuid):
    user = request.user

    # if user is the owner of the project, show all the details and give option to edit, else show only public details and no edit option
    project = Project.objects.select_related('org', 'owner').get(uuid=project_uuid)
    
    # Enforce access scoping
    if not rules.can_access_project(user, project):
        return HttpResponseForbidden("You do not have permission to view this project.")
        
    is_owner = user.is_authenticated and rules.is_project_owner(user, project)
    is_member = user.is_authenticated and rules.is_project_member(user, project)
    history = get_project_history(user, project)
    
    # Enrich history with component changes
    enriched_history = []
    for log in history:
        log_dict = {
            'log': log,
            'component_changes': None
        }
        if log.field_name == 'components':
            log_dict['component_changes'] = get_component_changes_for_project_log(project.id, log)
        enriched_history.append(log_dict)
    
    return render(request, 'project_details.html', {
        'project': project,
        'is_owner': is_owner,
        'is_member': is_member,
        'history': enriched_history,
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
    
    # Page-specific search
    q = request.GET.get('q', '').strip()
    if q:
        projects = projects.filter(
            Q(title__icontains=q) | Q(description__icontains=q)
        ).distinct()
        
    projects = projects.order_by('-updated_at')
    
    return render(request, 'projects_view.html', {
        'projects': projects,
        'title': 'My Projects',
        'subtitle': 'Manage projects owned by you.'
    })

@login_required
def collaborating_projects_view(request):
    projects = Project.objects.filter(collaborators=request.user).annotate(num_components=Count('project_components'))
    
    # Page-specific search
    q = request.GET.get('q', '').strip()
    if q:
        projects = projects.filter(
            Q(title__icontains=q) | Q(description__icontains=q)
        ).distinct()
        
    projects = projects.order_by('-updated_at')
    
    return render(request, 'projects_view.html', {
        'projects': projects,
        'title': 'Collaborating Projects',
        'subtitle': 'Projects you are collaborating on.'
    })
