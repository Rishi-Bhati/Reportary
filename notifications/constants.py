# Types that auto-mark-read when notification page is opened
AUTO_READ_TYPES = {
    'report_assigned', 'report_reassigned', 'report_status_changed',
    'report_commented', 'collaborator_added', 'report_impact_changed',
}

# Types that require user action (accept/decline) — NOT auto-read
ACTIONABLE_TYPES = {
    'invite_collaborator', 'invite_organisation', 'invite_project_head',
}
