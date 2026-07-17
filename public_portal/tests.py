from django.test import TestCase
from django.urls import reverse
from accounts.models import User
from projects.models import Project
from reports.models import Report
from public_portal.models import PublicReportingLink, AnonSubmission

class PublicPortalTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', email='owner@example.com', password='password')
        self.owner.is_email_verified = True
        self.owner.save()
        self.project = Project.objects.create(
            title='Public Link Project',
            link='https://example.com',
            description='desc',
            owner=self.owner,
            visibility='public',
            public=True,
            public_reporting_enabled=True
        )
        self.public_link = PublicReportingLink.objects.create(
            project=self.project,
            is_active=True,
            allow_anonymous=True
        )
        
        # Ensure anonymous internal user exists
        User.objects.get_or_create(email='anonymous@reportary.internal', defaults={'username': 'anonymous_system'})

    def test_portal_renders_successfully(self):
        url = reverse('public_portal:portal', kwargs={'token': self.public_link.token})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Submit a Report")
        self.assertContains(resp, "Spam check")

    def test_portal_post_validation_redirects_with_tracking_id(self):
        url = reverse('public_portal:portal', kwargs={'token': self.public_link.token})
        
        # Access portal first to populate CAPTCHA session
        session = self.client.session
        session[f'captcha_{self.public_link.token}'] = 4  # e.g. answer is 4
        session.save()
        
        # Post report
        resp = self.client.post(url, {
            'title': 'Portal Issue Title',
            'description': 'Portal description content',
            'steps': 'Steps content',
            'frequency': 'once',
            'impact': 'medium',
            'captcha_answer': 4,
            'website': '', # Honeypot empty
        })
        
        # Retrieve created report
        report = Report.objects.get(title='Portal Issue Title')
        self.assertTrue(report.is_anonymous)
        
        # Assert redirect includes tracking_id
        expected_redirect = reverse('public_portal:submitted', kwargs={'token': self.public_link.token}) + f'?tracking_id={report.uuid}'
        self.assertRedirects(resp, expected_redirect)

    def test_portal_honeypot_triggered_discards_silently(self):
        url = reverse('public_portal:portal', kwargs={'token': self.public_link.token})
        
        resp = self.client.post(url, {
            'title': 'Bot Issue Title',
            'description': 'Bot content',
            'captcha_answer': 4,
            'website': 'http://bot-honeypot-url.com', # Trigger honeypot
        })
        
        # Assert redirected to success page but NO report was created
        expected_redirect = reverse('public_portal:submitted', kwargs={'token': self.public_link.token})
        self.assertRedirects(resp, expected_redirect)
        self.assertFalse(Report.objects.filter(title='Bot Issue Title').exists())

    def test_submitted_page_renders_tracking_id(self):
        report_uuid = '019f2c5e-0000-0000-0000-000000000000'
        url = reverse('public_portal:submitted', kwargs={'token': self.public_link.token}) + f'?tracking_id={report_uuid}'
        
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, report_uuid)
        self.assertContains(resp, "Report Tracking ID")

    def test_portal_logged_in_user_redirects_to_new_report(self):
        self.client.force_login(self.owner)
        url = reverse('public_portal:portal', kwargs={'token': self.public_link.token})
        resp = self.client.get(url)
        expected_redirect = reverse('projects:reports:new', kwargs={'project_uuid': self.project.uuid}) + "?from_public_link=true"
        self.assertRedirects(resp, expected_redirect)

    def test_portal_logged_out_user_sees_login_link(self):
        url = reverse('public_portal:portal', kwargs={'token': self.public_link.token})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Want to report as a registered user?")
        
        import urllib.parse
        login_url_base = reverse('home:landing_page')
        report_new_url = reverse('projects:reports:new', kwargs={'project_uuid': self.project.uuid})
        encoded_next = urllib.parse.quote(f"{report_new_url}?from_public_link=true")
        expected_login_link = f"{login_url_base}?next={encoded_next}"
        self.assertContains(resp, expected_login_link)

    def test_portal_disabled_anon_reporting_redirects_logged_out_to_login(self):
        # Disable anonymous submissions on public link
        self.public_link.allow_anonymous = False
        self.public_link.save()
        
        url = reverse('public_portal:portal', kwargs={'token': self.public_link.token})
        resp = self.client.get(url)
        
        import urllib.parse
        login_url_base = reverse('home:landing_page')
        report_new_url = reverse('projects:reports:new', kwargs={'project_uuid': self.project.uuid})
        encoded_next = urllib.parse.quote(f"{report_new_url}?from_public_link=true")
        expected_redirect = f"{login_url_base}?next={encoded_next}"
        self.assertRedirects(resp, expected_redirect, fetch_redirect_response=False)

    def test_normal_report_anonymous_flag_saved_if_checked(self):
        self.client.force_login(self.owner)
        url = reverse('projects:reports:new', kwargs={'project_uuid': self.project.uuid})
        
        resp = self.client.post(url, {
            'title': 'Logged-in Anon Issue',
            'description': 'Description text',
            'steps': 'Steps text',
            'frequency': 'once',
            'impact': 'medium',
            'is_anonymous': True,
        })
        
        report = Report.objects.get(title='Logged-in Anon Issue')
        self.assertTrue(report.is_anonymous)
        self.assertEqual(report.reported_by, self.owner)

    def test_normal_report_anonymous_flag_forced_false_if_project_disabled(self):
        # Disable anonymous reporting on project
        self.project.anon_reporting_enabled = False
        self.project.save()
        
        self.client.force_login(self.owner)
        url = reverse('projects:reports:new', kwargs={'project_uuid': self.project.uuid})
        
        resp = self.client.post(url, {
            'title': 'Logged-in Forced Plain Issue',
            'description': 'Description text',
            'steps': 'Steps text',
            'frequency': 'once',
            'impact': 'medium',
            'is_anonymous': True, # Request anonymity anyway
        })
        
        report = Report.objects.get(title='Logged-in Forced Plain Issue')
        self.assertFalse(report.is_anonymous)
        self.assertEqual(report.reported_by, self.owner)

