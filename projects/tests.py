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
        url = reverse('projects:edit_project', kwargs={'pk': self.project.pk})
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
