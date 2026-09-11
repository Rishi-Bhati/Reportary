"""
Tests for the access-control predicates in rules/views.py.

Every project-scoped view in the application delegates its authorisation to
these functions, and they had no test coverage at all. These tests pin the
current, intended semantics so a refactor cannot loosen them silently.
"""
from django.contrib.auth.models import AnonymousUser
from django.test import TestCase

import rules.views as rules
from accounts.models import User
from comments.models import Comment
from organisations.models import Organisation
from projects.models import Project
from reports.models import Report


def make_user(username, verified=True):
    user = User.objects.create_user(
        username=username, email=f'{username}@example.com', password='Str0ngPassw!23')
    user.is_email_verified = verified
    user.save()
    return user


class ProjectRuleTests(TestCase):
    def setUp(self):
        self.owner = make_user('proj_owner')
        self.head = make_user('proj_head')
        self.collaborator = make_user('proj_collab')
        self.org_owner = make_user('proj_org_owner')
        self.org_member = make_user('proj_org_member')
        self.stranger = make_user('proj_stranger')
        self.anon = AnonymousUser()

        self.org = Organisation.objects.create(name='Rules Org', owner=self.org_owner)
        self.org.members.add(self.org_member)

        self.public = Project.objects.create(
            title='Public', owner=self.owner, link='http://x.com', description='d',
            visibility='public', public=True)
        self.private = Project.objects.create(
            title='Private', owner=self.owner, link='http://x.com', description='d',
            visibility='private', public=False, project_head=self.head)
        self.private.collaborators.add(self.collaborator)
        self.org_project = Project.objects.create(
            title='Org', owner=self.org_owner, link='http://x.com', description='d',
            visibility='org', public=False, org=self.org)

    # ── is_project_owner ─────────────────────────────────────────────────────
    def test_owner_is_project_owner(self):
        self.assertTrue(rules.is_project_owner(self.owner, self.private))

    def test_org_owner_is_project_owner_of_org_projects(self):
        self.assertTrue(rules.is_project_owner(self.org_owner, self.org_project))

    def test_project_head_is_not_project_owner(self):
        self.assertFalse(rules.is_project_owner(self.head, self.private))

    def test_collaborator_is_not_project_owner(self):
        self.assertFalse(rules.is_project_owner(self.collaborator, self.private))

    # ── is_project_manager ───────────────────────────────────────────────────
    def test_project_head_is_a_manager(self):
        self.assertTrue(rules.is_project_manager(self.head, self.private))

    def test_owner_is_a_manager(self):
        self.assertTrue(rules.is_project_manager(self.owner, self.private))

    def test_collaborator_is_not_a_manager(self):
        self.assertFalse(rules.is_project_manager(self.collaborator, self.private))

    # ── is_project_member ────────────────────────────────────────────────────
    def test_collaborator_is_a_member(self):
        self.assertTrue(rules.is_project_member(self.collaborator, self.private))

    def test_org_member_is_a_member_of_org_visible_projects(self):
        self.assertTrue(rules.is_project_member(self.org_member, self.org_project))

    def test_stranger_is_not_a_member(self):
        self.assertFalse(rules.is_project_member(self.stranger, self.private))

    def test_anonymous_is_never_a_member(self):
        self.assertFalse(rules.is_project_member(self.anon, self.public))

    # ── can_access_project ───────────────────────────────────────────────────
    def test_anyone_can_access_a_public_project(self):
        for actor in (self.owner, self.stranger, self.anon):
            self.assertTrue(rules.can_access_project(actor, self.public))

    def test_only_members_can_access_a_private_project(self):
        self.assertTrue(rules.can_access_project(self.owner, self.private))
        self.assertTrue(rules.can_access_project(self.head, self.private))
        self.assertTrue(rules.can_access_project(self.collaborator, self.private))
        self.assertFalse(rules.can_access_project(self.stranger, self.private))
        self.assertFalse(rules.can_access_project(self.anon, self.private))

    def test_only_org_members_can_access_an_org_project(self):
        self.assertTrue(rules.can_access_project(self.org_owner, self.org_project))
        self.assertTrue(rules.can_access_project(self.org_member, self.org_project))
        self.assertFalse(rules.can_access_project(self.stranger, self.org_project))
        self.assertFalse(rules.can_access_project(self.anon, self.org_project))

    # ── can_manage_public_links ──────────────────────────────────────────────
    def test_only_managers_manage_public_links(self):
        self.assertTrue(rules.can_manage_public_links(self.owner, self.private))
        self.assertTrue(rules.can_manage_public_links(self.head, self.private))
        self.assertFalse(rules.can_manage_public_links(self.collaborator, self.private))
        self.assertFalse(rules.can_manage_public_links(self.anon, self.private))


class ReportRuleTests(TestCase):
    def setUp(self):
        self.owner = make_user('rep_owner')
        self.head = make_user('rep_head')
        self.reporter = make_user('rep_reporter')
        self.stranger = make_user('rep_stranger')
        self.unverified = make_user('rep_unverified', verified=False)

        self.project = Project.objects.create(
            title='P', owner=self.owner, link='http://x.com', description='d',
            project_head=self.head)
        self.report = Report.objects.create(
            title='R', project=self.project, reported_by=self.reporter,
            description='d', steps='s')

    def test_only_the_reporter_can_edit(self):
        self.assertTrue(rules.can_edit_report(self.reporter, self.report))
        self.assertFalse(rules.can_edit_report(self.owner, self.report))
        self.assertFalse(rules.can_edit_report(self.stranger, self.report))

    def test_reporter_and_managers_can_delete(self):
        self.assertTrue(rules.can_delete_report(self.reporter, self.report))
        self.assertTrue(rules.can_delete_report(self.owner, self.report))
        self.assertTrue(rules.can_delete_report(self.head, self.report))
        self.assertFalse(rules.can_delete_report(self.stranger, self.report))

    def test_unverified_users_cannot_mutate_reports(self):
        unverified_report = Report.objects.create(
            title='R2', project=self.project, reported_by=self.unverified,
            description='d', steps='s')
        self.assertFalse(rules.can_edit_report(self.unverified, unverified_report))
        self.assertFalse(rules.can_delete_report(self.unverified, unverified_report))

    def test_anonymous_cannot_mutate_reports(self):
        self.assertFalse(rules.can_edit_report(AnonymousUser(), self.report))
        self.assertFalse(rules.can_delete_report(AnonymousUser(), self.report))

    def test_only_members_change_status(self):
        self.assertTrue(rules.can_change_status(self.owner, self.report))
        self.assertFalse(rules.can_change_status(self.stranger, self.report))

    def test_history_visible_to_members_and_the_reporter(self):
        self.assertTrue(rules.can_see_history(self.owner, self.report))
        self.assertTrue(rules.can_see_history(self.reporter, self.report))
        self.assertFalse(rules.can_see_history(self.stranger, self.report))


class CommentRuleTests(TestCase):
    def setUp(self):
        self.owner = make_user('com_owner')
        self.head = make_user('com_head')
        self.commenter = make_user('com_commenter')
        self.stranger = make_user('com_stranger')
        self.unverified = make_user('com_unverified', verified=False)

        self.project = Project.objects.create(
            title='P', owner=self.owner, link='http://x.com', description='d',
            project_head=self.head)
        self.report = Report.objects.create(
            title='R', project=self.project, reported_by=self.owner,
            description='d', steps='s')
        self.comment = Comment.objects.create(
            report=self.report, commented_by=self.commenter, text='hello')

    def test_only_the_commenter_can_edit(self):
        self.assertTrue(rules.can_edit_comment(self.commenter, self.comment))
        self.assertFalse(rules.can_edit_comment(self.owner, self.comment))
        self.assertFalse(rules.can_edit_comment(self.stranger, self.comment))

    def test_commenter_and_managers_can_delete(self):
        self.assertTrue(rules.can_delete_comment(self.commenter, self.comment))
        self.assertTrue(rules.can_delete_comment(self.owner, self.comment))
        self.assertTrue(rules.can_delete_comment(self.head, self.comment))
        self.assertFalse(rules.can_delete_comment(self.stranger, self.comment))

    def test_unverified_users_cannot_mutate_comments(self):
        comment = Comment.objects.create(
            report=self.report, commented_by=self.unverified, text='x')
        self.assertFalse(rules.can_edit_comment(self.unverified, comment))
        self.assertFalse(rules.can_delete_comment(self.unverified, comment))


class OrganisationRuleTests(TestCase):
    def setUp(self):
        self.owner = make_user('org_r_owner')
        self.member = make_user('org_r_member')
        self.stranger = make_user('org_r_stranger')
        self.org = Organisation.objects.create(name='Org', owner=self.owner)
        self.org.members.add(self.member)

    def test_membership(self):
        self.assertTrue(rules.is_organisation_member(self.owner, self.org))
        self.assertTrue(rules.is_organisation_member(self.member, self.org))
        self.assertFalse(rules.is_organisation_member(self.stranger, self.org))
        self.assertFalse(rules.is_organisation_member(AnonymousUser(), self.org))

    def test_only_the_owner_manages_the_org(self):
        self.assertTrue(rules.can_manage_organisation(self.owner, self.org))
        self.assertFalse(rules.can_manage_organisation(self.member, self.org))
        self.assertFalse(rules.can_manage_organisation_members(self.member, self.org))

    def test_members_can_view_details(self):
        self.assertTrue(rules.can_view_organisation_details(self.member, self.org))
        self.assertFalse(rules.can_view_organisation_details(self.stranger, self.org))
