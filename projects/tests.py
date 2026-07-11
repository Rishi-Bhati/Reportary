from django.test import TestCase
from django.urls import reverse
from accounts.models import User
from .models import Project, Component
from organisations.models import Organisation


class ProjectRegistrationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='tester', email='tester@example.com', password='password')
        self.client.force_login(self.user)

    def test_register_project_with_components(self):
        url = reverse('projects:new')
        data = {
            'title': 'Test Project',
            'link': 'https://example.com',
            'description': 'Project description',
            'visibility': 'public',
            'collaborators': '',
            'components-TOTAL_FORMS': '1',
            'components-INITIAL_FORMS': '0',
            'components-MIN_NUM_FORMS': '0',
            'components-MAX_NUM_FORMS': '1000',
            'components-0-name': 'Backend',
            'components-0-description': 'Backend description',
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)
        project = Project.objects.get(title='Test Project')
        self.assertEqual(project.description, 'Project description')
        components = project.components.all()
        self.assertEqual(components.count(), 1)
        comp = components.first()
        self.assertEqual(comp.name, 'Backend')
        self.assertEqual(comp.description, 'Backend description')


class ProjectEditTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', email='owner@example.com', password='password')
        self.other = User.objects.create_user(username='other', email='other@example.com', password='password')
        self.client.force_login(self.owner)
        self.project = Project.objects.create(title='Edit Project', link='https://example.com', description='Original', owner=self.owner)

    def test_edit_project_add_component_and_collaborator(self):
        url = reverse('projects:edit_project', kwargs={'project_uuid': self.project.uuid})
        data = {
            'title': 'Edit Project Updated',
            'link': 'https://example.com/new',
            'description': 'Updated description',
            'visibility': 'public',
            'collaborators': 'other@example.com',
            'components-TOTAL_FORMS': '1',
            'components-INITIAL_FORMS': '0',
            'components-MIN_NUM_FORMS': '0',
            'components-MAX_NUM_FORMS': '1000',
            'components-0-name': 'API',
            'components-0-description': 'API stuff',
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)

        # Accept the invitation
        from notifications.models import Invitation
        from notifications.services import accept_invitation
        invite = Invitation.objects.filter(invite_type='collaborator', invited_user=self.other).first()
        self.assertIsNotNone(invite)
        accept_invitation(invite, self.other)

        self.project.refresh_from_db()
        self.assertEqual(self.project.title, 'Edit Project Updated')
        self.assertTrue(self.project.collaborators.filter(email='other@example.com').exists())
        self.assertEqual(self.project.components.count(), 1)
        comp = self.project.components.first()
        self.assertEqual(comp.name, 'API')
        self.assertEqual(comp.description, 'API stuff')

class ProjectSearchAndCollaboratingTests(TestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(username='user1', email='user1@example.com', password='password')
        self.user2 = User.objects.create_user(username='user2', email='user2@example.com', password='password')
        
        self.project_owned = Project.objects.create(title='Owned Alpha', link='https://example.com', description='desc', owner=self.user1)
        self.project_owned_2 = Project.objects.create(title='Owned Beta', link='https://example.com', description='desc', owner=self.user1)
        
        self.project_collab = Project.objects.create(title='Collab Gamma', link='https://example.com', description='desc', owner=self.user2)
        self.project_collab.collaborators.add(self.user1)

    def test_my_projects_search(self):
        self.client.force_login(self.user1)
        url = reverse('projects:my_projects')
        
        # 1. No query
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context['projects']), 2)
        
        # 2. Filter query
        resp = self.client.get(url + '?q=Alpha')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context['projects']), 1)
        self.assertEqual(resp.context['projects'][0], self.project_owned)

    def test_collaborating_projects(self):
        self.client.force_login(self.user1)
        url = reverse('projects:collaborating_projects')
        
        # 1. No query
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context['projects']), 1)
        self.assertEqual(resp.context['projects'][0], self.project_collab)
        
        # 2. Query filter
        resp = self.client.get(url + '?q=Gamma')
        self.assertEqual(len(resp.context['projects']), 1)
        
        resp = self.client.get(url + '?q=Alpha')
        self.assertEqual(len(resp.context['projects']), 0)

    def test_project_head_sees_project_in_my_projects(self):
        org = Organisation.objects.create(name='Test Org', owner=self.user1)
        head_project = Project.objects.create(
            title='Head Project X',
            link='https://example.com',
            description='desc',
            owner=self.user1,
            project_head=self.user2,
            org=org,
            visibility='private',
            public=False
        )
        
        self.client.force_login(self.user2)
        url = reverse('projects:my_projects')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(head_project, resp.context['projects'])


class ProjectDashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='dashuser', email='dash@example.com', password='password')
        self.other_user = User.objects.create_user(username='otherdash', email='otherdash@example.com', password='password')
        self.project = Project.objects.create(title='Dashboard Project', link='https://example.com', description='desc', owner=self.user)
        
        # Add a couple of reports
        from reports.models import Report
        self.report1 = Report.objects.create(project=self.project, title='Report 1', severity='critical', status='open', reported_by=self.user)
        self.report2 = Report.objects.create(project=self.project, title='Report 2', severity='medium', status='resolved', reported_by=self.user)

    def test_project_dashboard_view_and_statistics(self):
        self.client.force_login(self.user)
        url = reverse('projects:project_detail', kwargs={'project_uuid': self.project.uuid})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        
        # Verify stats are passed in context
        self.assertEqual(resp.context['total_reports'], 2)
        self.assertEqual(resp.context['open_reports'], 1)
        self.assertEqual(resp.context['resolved_reports'], 1)
        self.assertEqual(resp.context['health_score'], 50)
        self.assertEqual(resp.context['health_rating'], 'Warning') # 1 open critical issue and 50% resolved ratio
        self.assertIn('recent_reports', resp.context)

    def test_project_tasks_actions(self):
        self.client.force_login(self.user)
        
        # 1. Add Task via POST
        add_url = reverse('projects:add_project_task', kwargs={'project_uuid': self.project.uuid})
        resp = self.client.post(add_url, {'title': 'Verify backup script'})
        self.assertEqual(resp.status_code, 200)
        
        from projects.models import ProjectTask
        task = ProjectTask.objects.filter(project=self.project, title='Verify backup script').first()
        self.assertIsNotNone(task)
        self.assertFalse(task.is_completed)

        # 2. Toggle Task via POST
        toggle_url = reverse('projects:toggle_project_task', kwargs={'project_uuid': self.project.uuid, 'task_id': task.id})
        resp = self.client.post(toggle_url)
        self.assertEqual(resp.status_code, 200)
        
        task.refresh_from_db()
        self.assertTrue(task.is_completed)

        # 3. Delete Task via POST
        delete_url = reverse('projects:delete_project_task', kwargs={'project_uuid': self.project.uuid, 'task_id': task.id})
        resp = self.client.post(delete_url)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(ProjectTask.objects.filter(id=task.id).exists())

    def test_project_tasks_permissions_scoping(self):
        # Stranger (other_user) cannot manage tasks
        self.client.force_login(self.other_user)
        add_url = reverse('projects:add_project_task', kwargs={'project_uuid': self.project.uuid})
        resp = self.client.post(add_url, {'title': 'Unauthorized task'})
        self.assertEqual(resp.status_code, 403)
