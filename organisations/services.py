"""
Services for organisation management.
Handles business logic for organisations including:
- Member management
- Organisation details updates
- Data retrieval and filtering
"""

from audit.services import log_action
import rules.views as rules
from accounts.models import User
from .models import Organisation
from projects.models import Project
from django.db import models


def get_user_organisations(user):
    """Get all organisations where user is owner or member."""
    return Organisation.objects.filter(
        models.Q(owner=user) | models.Q(members=user)
    ).distinct().order_by('-updated_at')


def get_user_owned_organisations(user):
    """Get all organisations owned by the user."""
    return Organisation.objects.filter(owner=user).order_by('-updated_at')


def get_organisation_members(organisation):
    """Get all members of an organisation (including owner)."""
    members = list(organisation.members.all())
    if organisation.owner not in members:
        members.insert(0, organisation.owner)
    return members


def get_organisation_projects(organisation):
    """Get all projects in an organisation."""
    return Project.objects.filter(org=organisation).order_by('-updated_at')


def update_organisation_details(*, organisation, name, description, domain, actor):
    """
    Update organisation details and log the changes.
    
    Args:
        organisation: Organisation instance to update
        name: New organisation name
        description: New organisation description
        domain: New organisation domain
        actor: User performing the update
    
    Returns:
        Updated organisation instance
    """
    if not rules.can_manage_organisation(actor, organisation):
        raise PermissionError("User is not authorized to manage this organisation")
    
    changes = {}
    
    # Track changes
    if name and name != organisation.name:
        changes['name'] = (organisation.name, name)
        organisation.name = name
    
    if description != organisation.description:
        changes['description'] = (organisation.description, description)
        organisation.description = description
    
    if domain and domain != organisation.domain:
        changes['domain'] = (organisation.domain, domain)
        organisation.domain = domain
    
    organisation.save()
    
    # Log changes
    for field, (old_value, new_value) in changes.items():
        log_action(
            actor=actor,
            action="update",
            entity_type="Organisation",
            entity_id=organisation.uuid,
            field_name=field,
            old_value=old_value,
            new_value=new_value,
        )
    
    return organisation


def add_organisation_member(*, organisation, member_email, actor):
    """
    Add a member to an organisation.
    
    Args:
        organisation: Organisation instance
        member_email: Email of the user to add
        actor: User performing the action
    
    Returns:
        Tuple (User instance, success boolean, message)
    """
    if not rules.can_manage_organisation_members(actor, organisation):
        return None, False, "You are not authorized to manage organisation members"
    
    try:
        user = User.objects.get(email=member_email)
        
        if not user.is_email_verified:
            return user, False, f"The user '{member_email}' has not verified their email yet and cannot be invited."
            
        if organisation.members.filter(id=user.id).exists() or user == organisation.owner:
            return user, False, "User is already a member of this organisation"
        
        from notifications.services import create_invitation
        create_invitation(
            invite_type='organisation',
            invited_by=actor,
            invited_user=user,
            organisation=organisation
        )
        
        return user, True, f"Invitation sent to {member_email} successfully."
    
    except User.DoesNotExist:
        return None, False, f"User with email {member_email} does not exist"


def remove_organisation_member(*, organisation, member_id, actor):
    """
    Remove a member from an organisation.
    
    Args:
        organisation: Organisation instance
        member_id: ID of the member to remove
        actor: User performing the action
    
    Returns:
        Tuple (success boolean, message)
    """
    if not rules.can_manage_organisation_members(actor, organisation):
        return False, "You are not authorized to manage organisation members"
    
    try:
        user = User.objects.get(id=member_id)
        
        if user == organisation.owner:
            return False, "Cannot remove the organisation owner"
        
        if not organisation.members.filter(id=user.id).exists():
            return False, "User is not a member of this organisation"
        
        organisation.members.remove(user)
        
        log_action(
            actor=actor,
            action="update",
            entity_type="Organisation",
            entity_id=organisation.uuid,
            field_name="members",
            old_value=f"Removed user: {user.email}",
            new_value=f"Member count: {organisation.members.count()}",
        )
        
        return True, f"Successfully removed {user.email} from the organisation"
    
    except User.DoesNotExist:
        return False, "User does not exist"


def create_organisation(*, name, description, owner, domain=None):
    """
    Create a new organisation.
    
    Args:
        name: Organisation name
        description: Organisation description
        owner: User that will be the owner
        domain: Optional domain for the organisation
    
    Returns:
        Created Organisation instance
    """
    organisation = Organisation.objects.create(
        name=name,
        description=description,
        owner=owner,
        domain=domain,
    )
    
    log_action(
        actor=owner,
        action="create",
        entity_type="Organisation",
        entity_id=organisation.uuid,
        field_name="name",
        new_value=name,
    )
    
    return organisation


def get_organisation_stats(organisation, user=None):
    """
    Get statistics about an organisation.
    
    Args:
        organisation: Organisation instance
        user: Optional user to filter projects visibility for
    
    Returns:
        Dictionary with various stats
    """
    projects = Project.objects.filter(org=organisation)
    if user and organisation.owner != user:
        from django.db.models import Q
        projects = projects.filter(
            Q(visibility='public') |
            Q(visibility='org') |
            Q(owner=user) |
            Q(project_head=user) |
            Q(collaborators=user)
        ).distinct()
    
    return {
        'members_count': organisation.members.count(),
        'owner': organisation.owner,
        'projects_count': projects.count(),
        'created_at': organisation.created_at,
        'updated_at': organisation.updated_at,
    }
