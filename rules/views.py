# This file serves all the rules for the while reportary project. all the rules and access controls regarding anything will be defined here.


### General Rules ###

def is_project_owner(user, project):
    return project.owner == user

### Rules for Reports ###

def is_reporter(user, report):
    return report.reported_by == user

### Rules for Comments ###

def is_commenter(user, comment):
    return comment.commented_by == user

