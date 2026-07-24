from django.test import TestCase
from django.urls import reverse
from accounts.models import User
from organisations.models import Organisation
from projects.models import Project
from reports.models import Report

class OrganisationProjectAccessTests(TestCase):
    def setUp(self):
        # Create users
        self.org_owner = User.objects.create_user(username='org_owner', email='owner@example.com', password='password')
        self.org_member = User.objects.create_user(username='org_member', email='member@example.com', password='password')
        self.non_member = User.objects.create_user(username='non_member', email='nonmember@example.com', password='password')
        
        # Create organisation and add member
        self.org = Organisation.objects.create(name='Test Org', owner=self.org_owner)
        self.org.members.add(self.org_member)

    def test_only_org_owner_can_register_project_for_org(self):
        # Log in as org member (not owner)
        self.client.force_login(self.org_member)
        url = reverse('projects:new') + f'?org={self.org.uuid}'
        
        # Try to register project
        data = {
            'title': 'Org Project',
            'link': 'https://example.com',
            'description': 'description',
            'org': self.org.id,
            'project_head': self.org_member.id,
            'visibility': 'private',
            'components-TOTAL_FORMS': '0',
            'components-INITIAL_FORMS': '0',
            'components-MIN_NUM_FORMS': '0',
            'components-MAX_NUM_FORMS': '1000',
        }
        
        resp = self.client.post(url, data)
        # Form validation should fail because self.org is not in the dropdown queryset of self.org_member (who doesn't own self.org)
        self.assertEqual(resp.status_code, 200) # Form re-rendered with error
        self.assertFormError(resp.context['form'], 'org', 'Select a valid choice. That choice is not one of the available choices.')

    def test_org_owner_can_register_project_and_assign_project_head(self):
        # Log in as org owner
        self.client.force_login(self.org_owner)
        url = reverse('projects:new') + f'?org={self.org.uuid}'
        
        data = {
            'title': 'Org Project A',
            'link': 'https://example.com',
            'description': 'description',
            'org': self.org.id,
            'project_head': self.org_member.id, # Assign org_member as project head
            'visibility': 'org',
            'components-TOTAL_FORMS': '0',
            'components-INITIAL_FORMS': '0',
            'components-MIN_NUM_FORMS': '0',
            'components-MAX_NUM_FORMS': '1000',
        }
        
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)
        
        # Verify project is created
        project = Project.objects.get(title='Org Project A')
        self.assertEqual(project.org, self.org)
        
        # Accept the designation invitation
        from notifications.models import Invitation
        from notifications.services import accept_invitation
        invite = Invitation.objects.filter(invite_type='project_head', invited_user=self.org_member).first()
        self.assertIsNotNone(invite)
        accept_invitation(invite, self.org_member)
        
        project.refresh_from_db()
        self.assertEqual(project.project_head, self.org_member)
        self.assertEqual(project.owner, self.org_owner) # Org owner is the main project owner

    def test_project_head_cannot_be_non_org_member(self):
        # Log in as org owner
        self.client.force_login(self.org_owner)
        url = reverse('projects:new') + f'?org={self.org.uuid}'
        
        data = {
            'title': 'Org Project B',
            'link': 'https://example.com',
            'description': 'description',
            'org': self.org.id,
            'project_head': self.non_member.id, # Assign non_member as project head
            'visibility': 'org',
            'components-TOTAL_FORMS': '0',
            'components-INITIAL_FORMS': '0',
            'components-MIN_NUM_FORMS': '0',
            'components-MAX_NUM_FORMS': '1000',
        }
        
        resp = self.client.post(url, data)
        # Form validation should fail because non_member is not a member of self.org
        self.assertEqual(resp.status_code, 200)
        self.assertFormError(resp.context['form'], 'project_head', 'Select a valid choice. That choice is not one of the available choices.')

    def test_private_org_project_access_scoping(self):
        # Create private org-owned project
        project = Project.objects.create(
            title='Private Org Project',
            link='https://example.com',
            description='desc',
            owner=self.org_owner,
            project_head=self.org_member,
            org=self.org,
            visibility='private',
            public=False
        )
        
        detail_url = reverse('projects:project_detail', kwargs={'project_uuid': project.uuid})
        
        # 1. Org member has access
        self.client.force_login(self.org_member)
        resp = self.client.get(detail_url)
        self.assertEqual(resp.status_code, 200)
        
        # 2. Org owner has access
        self.client.force_login(self.org_owner)
        resp = self.client.get(detail_url)
        self.assertEqual(resp.status_code, 200)
        
        # 3. Non-member is forbidden
        self.client.force_login(self.non_member)
        resp = self.client.get(detail_url)
        self.assertEqual(resp.status_code, 403)

    def test_anonymous_user_forbidden_from_private_org_project(self):
        project = Project.objects.create(
            title='Private Org Project',
            link='https://example.com',
            description='desc',
            owner=self.org_owner,
            project_head=self.org_member,
            org=self.org,
            visibility='private',
            public=False
        )
        
        detail_url = reverse('projects:project_detail', kwargs={'project_uuid': project.uuid})
        self.client.logout()
        resp = self.client.get(detail_url)
        self.assertEqual(resp.status_code, 302)

    def test_private_org_project_hidden_from_unrelated_members(self):
        # Create another org member who is not related to the project
        unrelated_member = User.objects.create_user(username='unrelated', email='unrelated@example.com', password='password')
        self.org.members.add(unrelated_member)
        
        # Create private org project owned by owner, head is owner, not org_member or unrelated
        project = Project.objects.create(
            title='Secret Project',
            link='https://example.com',
            description='desc',
            owner=self.org_owner,
            project_head=self.org_owner,
            org=self.org,
            visibility='private',
            public=False
        )
        
        # 1. Unrelated org member cannot access detail page (forbidden)
        self.client.force_login(unrelated_member)
        url = reverse('projects:project_detail', kwargs={'project_uuid': project.uuid})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 403)
        
        # 2. Unrelated org member cannot find it in org projects listing page
        org_projects_url = reverse('organisations:projects', kwargs={'uuid': self.org.uuid})
        resp = self.client.get(org_projects_url)
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn(project, resp.context['projects'])
        
        # 3. Unrelated org member cannot see it on their dashboard overview
        dashboard_overview_url = reverse('dashboard:overview')
        resp = self.client.get(dashboard_overview_url)
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn(project, resp.context['projects'])


class OrganisationAnonPolicyTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', email='owner@example.com', password='password')
        self.member = User.objects.create_user(username='member', email='member@example.com', password='password')
        self.org = Organisation.objects.create(name='Test Org', owner=self.owner)
        self.org.members.add(self.member)
        
    def test_owner_can_toggle_anon_reporting_policy(self):
        self.client.force_login(self.owner)
        url = reverse('organisations:toggle_anon', kwargs={'uuid': self.org.uuid})
        
        # Initially enabled
        self.assertTrue(self.org.anon_reporting_enabled)
        
        # Toggle it off
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)
        
        self.org.refresh_from_db()
        self.assertFalse(self.org.anon_reporting_enabled)
        
        # Toggle it back on
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)
        
        self.org.refresh_from_db()
        self.assertTrue(self.org.anon_reporting_enabled)

    def test_non_owner_cannot_toggle_anon_reporting_policy(self):
        self.client.force_login(self.member)
        url = reverse('organisations:toggle_anon', kwargs={'uuid': self.org.uuid})
        
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(self.org.anon_reporting_enabled)

    def test_details_page_updates_anon_reporting_policy(self):
        self.client.force_login(self.owner)
        url = reverse('organisations:details', kwargs={'uuid': self.org.uuid})
        
        # Update via details form - set it to False (checkbox not in POST)
        resp = self.client.post(url, {
            'name': 'Updated Org',
            'description': 'desc',
            'domain': 'domain.com',
            # anon_reporting_enabled omitted -> False
        })
        self.assertEqual(resp.status_code, 302)
        self.org.refresh_from_db()
        self.assertEqual(self.org.name, 'Updated Org')
        self.assertFalse(self.org.anon_reporting_enabled)
        
        # Update via details form - set it to True (on)
        resp = self.client.post(url, {
            'name': 'Updated Org',
            'description': 'desc',
            'domain': 'domain.com',
            'anon_reporting_enabled': 'on'
        })
        self.assertEqual(resp.status_code, 302)
        self.org.refresh_from_db()
        self.assertTrue(self.org.anon_reporting_enabled)

