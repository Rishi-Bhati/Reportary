from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from projects.models import Project
from reports.models import Report

User = get_user_model()

class DashboardAnalyticsTests(TestCase):
    def setUp(self):
        # Create user
        self.user = User.objects.create_user(
            username='dashuser',
            email='dash@example.com',
            password='Password123!',
            is_email_verified=True
        )
        
        # Create other user for privacy tests
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@example.com',
            password='Password123!',
            is_email_verified=True
        )

        # Create public project
        self.public_project = Project.objects.create(
            owner=self.user,
            title="Public Proj",
            visibility="public"
        )

        # Create private project owned by other_user
        self.private_project = Project.objects.create(
            owner=self.other_user,
            title="Private Proj",
            visibility="private"
        )

        # Create report in public project (assigned to user)
        self.report1 = Report.objects.create(
            project=self.public_project,
            reported_by=self.user,
            assigned_to=self.user,
            title="Public Report 1",
            description="Details",
            steps="Steps",
            severity="critical",
            impact="critical",
            status="open"
        )

        # Create report in private project (not accessible by user)
        self.report2 = Report.objects.create(
            project=self.private_project,
            reported_by=self.other_user,
            title="Private Report 1",
            description="Details",
            steps="Steps",
            severity="high",
            impact="high",
            status="open"
        )

    def test_dashboard_access_and_context(self):
        """Test dashboard view returns 200 and has correct metrics context."""
        self.client.force_login(self.user)
        # Test dashboard shell
        response = self.client.get(reverse('dashboard:dashboard'))
        self.assertEqual(response.status_code, 200)

        # Test dashboard overview partial
        response_overview = self.client.get(reverse('dashboard:overview'))
        self.assertEqual(response_overview.status_code, 200)
        self.assertEqual(response_overview.context['assigned_reports_count'], 1)
        self.assertEqual(response_overview.context['my_reports_count'], 1)

        # Test dashboard analytics partial
        response_analytics = self.client.get(reverse('dashboard:analytics'))
        self.assertEqual(response_analytics.status_code, 200)
        self.assertEqual(response_analytics.context['total_reports_count'], 1)  # Only public_project report counted
        self.assertEqual(response_analytics.context['severity_counts']['critical'], 1)
        self.assertEqual(response_analytics.context['severity_counts']['high'], 0)  # Private report high severity is ignored

    def test_session_recently_viewed_tracking(self):
        """Test visiting a report detail registers in the session recently viewed list."""
        self.client.force_login(self.user)
        
        # Visit report 1
        url = reverse('reports:report_detail', kwargs={'report_uuid': self.report1.uuid})
        self.client.get(url)
        
        # Now visit dashboard overview partial and check recently viewed
        response = self.client.get(reverse('dashboard:overview'))
        recently_viewed = response.context['recently_viewed_reports']
        self.assertEqual(len(recently_viewed), 1)
        self.assertEqual(recently_viewed[0].uuid, self.report1.uuid)
