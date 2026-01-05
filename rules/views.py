# This file serves all the rules for the while reportary project. all the rules and access controls regarding anything will be defined here.


### General Rules ###

def is_project_owner(user, project):
    return project.owner == user

def is_project_member(user, project):
    # For now, we'll consider the project owner as the only member.
    # This can be extended later to include other roles.

    return project.collaborators.filter(id=user.id).exists() or is_project_owner(user, project)
    
    
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
