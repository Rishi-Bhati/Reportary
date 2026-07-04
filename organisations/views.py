from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden
from .models import Organisation
from .forms import OrganisationForm
from . import services
import rules.views as rules


@login_required
def create_organisation(request):
    """Create a new organisation."""
    
    if request.method == 'POST':
        form = OrganisationForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            description = form.cleaned_data.get('description', '')
            domain = form.cleaned_data.get('domain', '')
            
            org = services.create_organisation(
                name=name,
                description=description,
                owner=request.user,
                domain=domain
            )
            
            messages.success(request, f"Organisation '{name}' created successfully!")
            return redirect('organisations:dashboard', uuid=org.uuid)
    else:
        form = OrganisationForm()
    
    return render(request, 'organisations/create_organisation.html', {
        'form': form,
    })


@login_required
def organisation_list(request):
    """Display all organisations owned by the user."""
    organisations = services.get_user_owned_organisations(request.user)
    return render(request, 'organisations/organisation_list.html', {
        'organisations': organisations,
    })


@login_required
def organisation_dashboard(request, uuid):
    """Main organisation dashboard - entry point for organisation management."""
    org = get_object_or_404(Organisation, uuid=uuid)
    
    # Check if user has access to view organisation
    if not rules.can_view_organisation_details(request.user, org):
        return HttpResponseForbidden("You don't have permission to view this organisation.")
    
    # Get stats and related data
    stats = services.get_organisation_stats(org)
    projects = services.get_organisation_projects(org)
    members = services.get_organisation_members(org)
    
    return render(request, 'organisations/organisation_dashboard.html', {
        'organisation': org,
        'stats': stats,
        'projects': projects,
        'members': members,
        'is_owner': rules.is_organisation_owner(request.user, org),
        'is_member': rules.is_organisation_member(request.user, org),
    })


@login_required
def organisation_details(request, uuid):
    """View and edit organisation details."""
    org = get_object_or_404(Organisation, uuid=uuid)
    
    if not rules.can_manage_organisation(request.user, org):
        return HttpResponseForbidden("You don't have permission to manage this organisation.")
    
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        description = request.POST.get('description', '').strip()
        domain = request.POST.get('domain', '').strip()
        
        if not name:
            messages.error(request, "Organisation name cannot be empty.")
            return render(request, 'organisations/organisation_details.html', {'organisation': org})
        
        try:
            org = services.update_organisation_details(
                organisation=org,
                name=name,
                description=description,
                domain=domain,
                actor=request.user
            )
            messages.success(request, "Organisation details updated successfully.")
            return redirect('organisations:dashboard', uuid=org.uuid)
        except PermissionError as e:
            messages.error(request, str(e))
    
    return render(request, 'organisations/organisation_details.html', {
        'organisation': org,
        'is_owner': rules.is_organisation_owner(request.user, org),
    })


@login_required
def organisation_members(request, uuid):
    """Manage organisation members."""
    org = get_object_or_404(Organisation, uuid=uuid)
    
    if not rules.can_manage_organisation_members(request.user, org):
        return HttpResponseForbidden("You don't have permission to manage organisation members.")
    
    if request.method == 'POST':
        action = request.POST.get('action', '')
        
        if action == 'add':
            member_email = request.POST.get('member_email', '').strip()
            if member_email:
                user, success, message = services.add_organisation_member(
                    organisation=org,
                    member_email=member_email,
                    actor=request.user
                )
                if success:
                    messages.success(request, message)
                else:
                    messages.error(request, message)
        
        elif action == 'remove':
            member_id = request.POST.get('member_id')
            if member_id:
                success, message = services.remove_organisation_member(
                    organisation=org,
                    member_id=member_id,
                    actor=request.user
                )
                if success:
                    messages.success(request, message)
                else:
                    messages.error(request, message)
        
        return redirect('organisations:members', uuid=org.uuid)
    
    members = services.get_organisation_members(org)
    
    return render(request, 'organisations/organisation_members.html', {
        'organisation': org,
        'members': members,
        'is_owner': rules.is_organisation_owner(request.user, org),
    })


@login_required
def organisation_projects(request, uuid):
    """View organisation projects."""
    org = get_object_or_404(Organisation, uuid=uuid)
    
    if not rules.can_view_organisation_details(request.user, org):
        return HttpResponseForbidden("You don't have permission to view this organisation.")
    
    projects = services.get_organisation_projects(org)
    
    from django.db.models import Q
    q = request.GET.get('q', '').strip()
    if q:
        projects = projects.filter(
            Q(title__icontains=q) | Q(description__icontains=q)
        ).distinct()
    
    return render(request, 'organisations/organisation_projects.html', {
        'organisation': org,
        'projects': projects,
        'is_owner': rules.is_organisation_owner(request.user, org),
    })


@login_required
@require_POST
def leave_organisation(request, uuid):
    """Leave an organisation."""
    org = get_object_or_404(Organisation, uuid=uuid)
    
    if request.user == org.owner:
        messages.error(request, "Organisation owners cannot leave their organisation.")
        return redirect('organisations:dashboard', uuid=org.uuid)
    
    if request.user in org.members.all():
        org.members.remove(request.user)
        messages.success(request, f"You have left {org.name}.")
    else:
        messages.error(request, "You are not a member of this organisation.")
        
    return redirect('dashboard:home')

