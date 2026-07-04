from django.test import TestCase
from django.urls import reverse
from accounts.models import User
from .models import Project, Component


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
            'public': 'on',
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
            'public': 'on',
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
