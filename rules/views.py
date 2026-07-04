# This file serves all the rules for the while reportary project. all the rules and access controls regarding anything will be defined here.


### General Rules ###

def is_project_owner(user, project):
    if project.owner == user:
        return True
    if project.project_head == user:
        return True
    if project.org and is_organisation_owner(user, project.org):
        return True
    return False

def is_project_member(user, project):
    if project.collaborators.filter(id=user.id).exists() or is_project_owner(user, project):
        return True
    if project.visibility == 'org' and project.org:
        return is_organisation_member(user, project.org)
    return False
    
    
def can_access_project(user, project):
    if project.visibility == 'public':
        return True
    if not user or not user.is_authenticated:
        return False
    if project.visibility == 'org':
        if project.org:
            return is_organisation_member(user, project.org)
        return is_project_owner(user, project) or project.collaborators.filter(id=user.id).exists()
    if project.visibility == 'private':
        return is_project_owner(user, project) or project.collaborators.filter(id=user.id).exists()
    
    # Backwards compatibility fallback
    if project.public:
        return True
    return False


def is_assigned_to(user, report):
    return report.assigned_to == user

### Rules for Reports ###

def is_reporter(user, report):
    return report.reported_by == user

def can_change_status(user, report):
    # Only project members (currently, the owner) can change the status.
    return is_project_member(user, report.project)

### Rules for Comments ###

def is_commenter(user, comment):
    return comment.commented_by == user


def can_see_history(user, report):
    return is_project_member(user, report.project) or is_reporter(user, report)


### Rules for Organisations ###

def is_organisation_owner(user, organisation):
    """Check if user is the owner of the organisation."""
    return organisation.owner == user


def is_organisation_member(user, organisation):
    """Check if user is a member of the organisation."""
    return organisation.members.filter(id=user.id).exists() or is_organisation_owner(user, organisation)


def can_manage_organisation(user, organisation):
    """Check if user can manage/edit the organisation (only owner can)."""
    return is_organisation_owner(user, organisation)


def can_manage_organisation_members(user, organisation):
    """Check if user can add/remove members from the organisation."""
    return is_organisation_owner(user, organisation)


def can_view_organisation_details(user, organisation):
    """Check if user can view organisation details."""
    return is_organisation_member(user, organisation)
