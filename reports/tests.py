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
        url = reverse('projects:reports:report_list', kwargs={'project_pk': self.project.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        reports = resp.context['reports']
        self.assertIn(self.visible_report, reports)
        self.assertNotIn(self.hidden_report, reports)

    def test_owner_sees_all_reports(self):
        self.client.force_login(self.owner)
        url = reverse('projects:reports:report_list', kwargs={'project_pk': self.project.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        reports = resp.context['reports']
        self.assertIn(self.visible_report, reports)
        self.assertIn(self.hidden_report, reports)

    def test_reporter_sees_their_hidden_report(self):
        self.client.force_login(self.reporter)
        url = reverse('projects:reports:report_list', kwargs={'project_pk': self.project.pk})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        reports = resp.context['reports']
        self.assertIn(self.visible_report, reports)
        self.assertIn(self.hidden_report, reports)
