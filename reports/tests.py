from django.test import TestCase
from django.urls import reverse
from accounts.models import User
from projects.models import Project
from reports.models import Report


class ReportListTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', email='owner@example.com', password='password')
        self.reporter = User.objects.create_user(username='reporter', email='reporter@example.com', password='password')
        self.other = User.objects.create_user(username='other', email='other@example.com', password='password')

        self.project = Project.objects.create(title='Project A', link='https://example.com', description='desc', owner=self.owner)

        # Visible report by reporter
        self.visible_report = Report.objects.create(project=self.project, title='Visible', description='vis', reported_by=self.reporter, visibility=True)
        # Hidden report by reporter
        self.hidden_report = Report.objects.create(project=self.project, title='Hidden', description='hid', reported_by=self.reporter, visibility=False)

    def test_anonymous_sees_visible_only(self):
        url = reverse('projects:reports:report_list', kwargs={'project_uuid': self.project.uuid})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        reports = resp.context['reports']
        self.assertIn(self.visible_report, reports)
        self.assertNotIn(self.hidden_report, reports)

    def test_owner_sees_all_reports(self):
        self.client.force_login(self.owner)
        url = reverse('projects:reports:report_list', kwargs={'project_uuid': self.project.uuid})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        reports = resp.context['reports']
        self.assertIn(self.visible_report, reports)
        self.assertIn(self.hidden_report, reports)

    def test_reporter_sees_their_hidden_report(self):
        self.client.force_login(self.reporter)
        url = reverse('projects:reports:report_list', kwargs={'project_uuid': self.project.uuid})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        reports = resp.context['reports']
        self.assertIn(self.visible_report, reports)
        self.assertIn(self.hidden_report, reports)


class ReportDetailTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='report_owner', email='report_owner@example.com', password='password')
        self.collaborator = User.objects.create_user(username='collab', email='collab@example.com', password='password')
        
        self.project = Project.objects.create(title='Project A', link='https://example.com', description='desc', owner=self.owner)
        self.project.collaborators.add(self.collaborator)
        
        self.report = Report.objects.create(
            project=self.project, 
            title='Report 1', 
            description='desc', 
            reported_by=self.owner,
            visibility=True
        )

    def test_collaborators_in_context(self):
        self.client.force_login(self.owner)
        url = reverse('projects:reports:report_detail', kwargs={'project_uuid': self.project.uuid, 'report_uuid': self.report.uuid})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        
        # Check if collaborators are correctly passed to context
        collaborators = resp.context['collaborators']
        
        self.assertIn(self.collaborator, collaborators)

class ReportsSearchAndNeedsAttentionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='testuser@example.com', password='password')
        self.user2 = User.objects.create_user(username='user2', email='user2@example.com', password='password')
        
        self.project_owned = Project.objects.create(title='Owned Project', link='https://example.com', description='desc', owner=self.user)
        self.project_other = Project.objects.create(title='Other Project', link='https://example.com', description='desc', owner=self.user2)
        self.project_other.collaborators.add(self.user)
        
        # Reports
        self.critical_assigned = Report.objects.create(project=self.project_other, title='Critical assigned', severity='critical', assigned_to=self.user, reported_by=self.user2, visibility=True)
        self.critical_on_my_project = Report.objects.create(project=self.project_owned, title='Critical on owned', severity='critical', reported_by=self.user2, visibility=True)
        self.normal_report = Report.objects.create(project=self.project_owned, title='Normal report', severity='medium', reported_by=self.user2, visibility=True)

    def test_my_reports_search(self):
        self.client.force_login(self.user)
        # Create a report created by self.user
        my_rep = Report.objects.create(project=self.project_owned, title='My Special Report', severity='low', reported_by=self.user, visibility=True)
        
        url = reverse('reports:my_reports')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context['reports']), 1)
        self.assertEqual(resp.context['reports'][0], my_rep)
        
        resp = self.client.get(url + '?q=Special')
        self.assertEqual(len(resp.context['reports']), 1)
        
        resp = self.client.get(url + '?q=NonExistent')
        self.assertEqual(len(resp.context['reports']), 0)

    def test_needs_attention(self):
        self.client.force_login(self.user)
        url = reverse('reports:needs_attention')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        
        # Needs attention should include critical assigned and critical on user's projects, but not normal severity reports
        reports = resp.context['reports']
        self.assertEqual(len(reports), 2)
        self.assertIn(self.critical_assigned, reports)
        self.assertIn(self.critical_on_my_project, reports)
        self.assertNotIn(self.normal_report, reports)
