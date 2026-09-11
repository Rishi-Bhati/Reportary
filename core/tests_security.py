"""
Regression tests for the security findings fixed in the hardening pass.

Each test names the finding it locks down. They live together rather than in
their owning apps because they are cross-cutting and because keeping them in one
place makes it obvious when one is deleted.
"""
from django.test import Client, TestCase

from accounts.models import User
from components.models import Component
from projects.models import Project
from reports.models import Report


def _user(email, username, **extra):
    u = User.objects.create_user(email=email, username=username, password='Str0ngPassw!23', **extra)
    u.is_email_verified = True
    u.save()
    return u


class ReportCreationAccessControlTests(TestCase):
    """SEC-01 — the project picker route must authorise the submitted project."""

    def setUp(self):
        self.attacker = _user('attacker@example.com', 'attacker')
        self.victim = _user('victim@example.com', 'victim')
        self.client.force_login(self.attacker)

    def _post_report(self, project, title):
        return self.client.post('/reports/new/', {
            'project': project.id,
            'title': title,
            'description': 'body',
            'steps': 'steps',
            'frequency': 'once',
            'impact': 'low',
            'visibility': 'on',
        })

    def test_cannot_create_report_in_private_project(self):
        private = Project.objects.create(
            owner=self.victim, title='Secret', link='http://x.com', description='d',
            visibility='private', public=False,
        )
        response = self._post_report(private, 'IDOR probe')
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Report.objects.filter(project=private).exists())

    def test_cannot_create_report_in_org_only_project(self):
        from organisations.models import Organisation
        org = Organisation.objects.create(owner=self.victim, name='Org')
        org_project = Project.objects.create(
            owner=self.victim, title='Org only', link='http://x.com', description='d',
            visibility='org', public=False, org=org,
        )
        response = self._post_report(org_project, 'Org probe')
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Report.objects.filter(project=org_project).exists())

    def test_can_still_create_report_in_public_project(self):
        public = Project.objects.create(
            owner=self.victim, title='Open', link='http://x.com', description='d',
            visibility='public', public=True,
        )
        response = self._post_report(public, 'Legitimate report')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Report.objects.filter(project=public, title='Legitimate report').exists())

    def test_garbage_project_id_does_not_500(self):
        response = self.client.post('/reports/new/', {
            'project': 'not-an-id', 'title': 'x', 'description': 'd',
            'steps': 's', 'frequency': 'once', 'impact': 'low',
        })
        self.assertIn(response.status_code, (200, 302, 403))


class MarkdownRenderingTests(TestCase):
    """SEC-02 — untrusted Markdown is sanitised on the server, not in the browser."""

    def setUp(self):
        self.owner = _user('owner@example.com', 'owner')
        self.project = Project.objects.create(
            owner=self.owner, title='P', link='http://x.com', description='d')
        self.client.force_login(self.owner)

    def test_raw_html_in_description_is_escaped(self):
        report = Report.objects.create(
            title='xss probe', project=self.project, reported_by=self.owner,
            description='<img src=x onerror=alert(1)>', steps='<script>alert(2)</script>')
        body = self.client.get(
            f'/projects/{self.project.uuid}/reports/{report.uuid}/').content.decode()

        self.assertNotIn('<img src=x onerror=alert(1)>', body)
        self.assertNotIn('<script>alert(2)</script>', body)
        self.assertIn('&lt;img src=x onerror=alert(1)&gt;', body)

    def test_no_client_side_markdown_sink_remains(self):
        report = Report.objects.create(
            title='sink probe', project=self.project, reported_by=self.owner,
            description='hello', steps='s')
        body = self.client.get(
            f'/projects/{self.project.uuid}/reports/{report.uuid}/').content.decode()

        self.assertNotIn('marked.parse', body)
        self.assertNotIn('innerHTML', body)

    def test_markdown_still_renders(self):
        report = Report.objects.create(
            title='md probe', project=self.project, reported_by=self.owner,
            description='**bold**', steps='s')
        body = self.client.get(
            f'/projects/{self.project.uuid}/reports/{report.uuid}/').content.decode()
        self.assertIn('<strong>bold</strong>', body)

    def test_javascript_urls_are_not_linked(self):
        from core.templatetags.markdown_tags import markdown
        rendered = str(markdown('[click](javascript:alert(1))'))
        self.assertNotIn('href="javascript:', rendered)

    def test_links_get_noopener(self):
        from core.templatetags.markdown_tags import markdown
        rendered = str(markdown('[ok](https://example.com)'))
        self.assertIn('rel="nofollow noopener noreferrer"', rendered)


class AnalyticsChartEscapingTests(TestCase):
    """SEC-03 — chart data goes through json_script, not |safe."""

    def test_component_name_cannot_break_out_of_script_block(self):
        owner = _user('charts@example.com', 'charts')
        project = Project.objects.create(
            owner=owner, title='P', link='http://x.com', description='d')
        payload = '</script><script>alert(1)</script>'
        component = Component.objects.create(project=project, name=payload, description='d')
        Report.objects.create(title='r1', project=project, reported_by=owner,
                              description='d', steps='s', component=component)

        self.client.force_login(owner)
        body = self.client.get('/dashboard/analytics/').content.decode()

        self.assertNotIn(payload, body)
        self.assertIn('\\u003C/script\\u003E', body)


class FilterDropdownScopingTests(TestCase):
    """SEC-10 — filter dropdowns must not enumerate every user in the system."""

    def test_unrelated_users_are_not_listed_on_a_public_project(self):
        owner = _user('scopeowner@example.com', 'scopeowner')
        unrelated = _user('nobody@example.com', 'unrelated_person')
        project = Project.objects.create(
            owner=owner, title='Public', link='http://x.com', description='d',
            visibility='public', public=True)
        Report.objects.create(title='r', project=project, reported_by=owner,
                              description='d', steps='s')

        body = Client().get(f'/projects/{project.uuid}/reports/').content.decode()

        self.assertNotIn(unrelated.username, body)
        self.assertIn(owner.username, body)


class AnonymousPortalTests(TestCase):
    """SEC-07 and SEC-08 — the least-trusted path was the least-validated one."""

    def setUp(self):
        from public_portal.services import get_or_create_link

        self.owner = _user('portalowner@example.com', 'portalowner')
        self.project = Project.objects.create(
            owner=self.owner, title='Portal', link='http://x.com', description='d',
            anon_reporting_enabled=True, public_reporting_enabled=True,
            anon_attachments_enabled=True)
        self.link = get_or_create_link(self.project)
        self.url = f'/p/{self.link.token}/'
        self.anon = Client()

    def _captcha_answer(self):
        self.anon.get(self.url)
        return self.anon.session.get(f'captcha_{self.link.token}')

    def _submit(self, **extra):
        data = {
            'title': 'anon report', 'description': 'd', 'steps': '',
            'frequency': 'once', 'impact': 'low', 'website': '',
            'captcha_answer': self._captcha_answer(),
        }
        data.update(extra)
        return self.anon.post(self.url, data)

    def test_disallowed_file_type_is_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from reports.models import ReportAttachment

        evil = SimpleUploadedFile(
            'payload.svg', b'<svg xmlns="http://www.w3.org/2000/svg" onload="alert(1)"/>',
            'image/svg+xml')
        self._submit(attachment=evil)

        self.assertNotIn('.svg', self.project.allowed_attachment_types)
        self.assertFalse(ReportAttachment.objects.filter(filename='payload.svg').exists())

    def test_allowed_file_type_still_works(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from reports.models import ReportAttachment

        self._submit(attachment=SimpleUploadedFile('shot.png', b'\x89PNG fake', 'image/png'))
        self.assertTrue(ReportAttachment.objects.filter(filename='shot.png').exists())

    def test_hidden_report_titles_are_not_leaked(self):
        Report.objects.create(
            title='Internal only 0day', project=self.project, reported_by=self.owner,
            description='secret', steps='s', visibility=False)

        response = self._submit(title='Internal only 0day')
        self.assertNotIn('already exists', response.content.decode())
        self.assertTrue(
            Report.objects.filter(project=self.project, is_anonymous=True).exists(),
            'the submission should go through rather than reveal the collision',
        )


class LoginHardeningTests(TestCase):
    """SEC-09 (login half) and SEC-15."""

    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.user = _user('login@example.com', 'loginuser')

    def tearDown(self):
        from django.core.cache import cache
        cache.clear()

    def _login(self, password, **extra):
        data = {'email': self.user.email, 'password': password}
        data.update(extra)
        return self.client.post('/auth/submit/login/', data)

    def test_valid_credentials_still_work(self):
        response = self._login('Str0ngPassw!23')
        self.assertEqual(response.status_code, 204)

    def test_repeated_failures_are_throttled(self):
        from home.views import LOGIN_ATTEMPT_LIMIT_PER_ACCOUNT

        for _ in range(LOGIN_ATTEMPT_LIMIT_PER_ACCOUNT):
            self._login('wrong-password')

        body = self._login('wrong-password').content.decode()
        self.assertIn('Too many failed sign-in attempts', body)

    def test_throttle_blocks_even_a_correct_password(self):
        from home.views import LOGIN_ATTEMPT_LIMIT_PER_ACCOUNT

        for _ in range(LOGIN_ATTEMPT_LIMIT_PER_ACCOUNT):
            self._login('wrong-password')
        self.assertEqual(self._login('Str0ngPassw!23').status_code, 200)

    def test_a_successful_login_clears_the_counter(self):
        self._login('wrong-password')
        self._login('Str0ngPassw!23')
        self.assertEqual(self._login('Str0ngPassw!23').status_code, 204)

    def test_soft_deleted_account_is_not_reactivated_without_confirmation(self):
        from django.utils import timezone
        from datetime import timedelta

        deletion_date = timezone.now() + timedelta(days=30)
        self.user.is_active = False
        self.user.scheduled_deletion_date = deletion_date
        self.user.save()

        response = self._login('Str0ngPassw!23')
        self.assertEqual(response.status_code, 200)
        self.assertIn('scheduled for deletion', response.content.decode())

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        self.assertIsNotNone(self.user.scheduled_deletion_date)

    def test_confirmed_reactivation_restores_the_account(self):
        self.user.is_active = False
        self.user.save()

        response = self._login('Str0ngPassw!23', confirm_reactivate='yes')
        self.assertEqual(response.status_code, 204)

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        self.assertIsNone(self.user.scheduled_deletion_date)


class ClientIpTests(TestCase):
    """SEC-12 — audit logs and rate limits must use the trusted proxy hop."""

    def test_rightmost_forwarded_entry_wins(self):
        from django.test import RequestFactory

        from core.http import get_client_ip

        request = RequestFactory().get(
            '/', HTTP_X_FORWARDED_FOR='1.2.3.4, 5.6.7.8, 9.9.9.9', REMOTE_ADDR='10.0.0.1')
        self.assertEqual(get_client_ip(request), '9.9.9.9')

    def test_falls_back_to_remote_addr(self):
        from django.test import RequestFactory

        from core.http import get_client_ip

        request = RequestFactory().get('/', REMOTE_ADDR='10.0.0.1')
        self.assertEqual(get_client_ip(request), '10.0.0.1')

    def test_all_call_sites_agree(self):
        from django.test import RequestFactory

        from core.http import get_client_ip
        from core.middleware import GeoLanguageMiddleware
        from public_portal.services import _get_client_ip as portal_ip
        from restapi.auth import _get_client_ip as api_ip

        request = RequestFactory().get(
            '/', HTTP_X_FORWARDED_FOR='1.2.3.4, 9.9.9.9', REMOTE_ADDR='10.0.0.1')
        expected = get_client_ip(request)

        self.assertEqual(portal_ip(request), expected)
        self.assertEqual(api_ip(request), expected)
        self.assertEqual(
            GeoLanguageMiddleware(lambda r: None)._get_client_ip(request), expected)


class PaginationTests(TestCase):
    """PERF-02 — list views must not render an unbounded queryset."""

    def setUp(self):
        from core.pagination import DEFAULT_PER_PAGE

        self.per_page = DEFAULT_PER_PAGE
        self.owner = _user('paging@example.com', 'paginguser')
        self.project = Project.objects.create(
            owner=self.owner, title='Paged', link='http://x.com', description='d',
            visibility='public', public=True)
        for i in range(self.per_page + 7):
            Report.objects.create(
                title=f'Report {i:03d}', project=self.project, reported_by=self.owner,
                description='d', steps='s')
        self.client.force_login(self.owner)
        self.url = f'/projects/{self.project.uuid}/reports/'

    def test_first_page_is_capped(self):
        page = self.client.get(self.url).context['reports']
        self.assertEqual(len(page.object_list), self.per_page)

    def test_second_page_holds_the_remainder(self):
        page = self.client.get(f'{self.url}?page=2').context['reports']
        self.assertEqual(len(page.object_list), 7)

    def test_out_of_range_page_clamps_instead_of_erroring(self):
        response = self.client.get(f'{self.url}?page=9999')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['reports'].number,
                         response.context['paginator'].num_pages)

    def test_non_integer_page_falls_back_to_the_first(self):
        response = self.client.get(f'{self.url}?page=banana')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['reports'].number, 1)

    def test_filters_survive_paging(self):
        context = self.client.get(f'{self.url}?status=open&sort_by=oldest&page=2').context
        self.assertIn('status=open', context['pagination_querystring'])
        self.assertIn('sort_by=oldest', context['pagination_querystring'])
        self.assertNotIn('page=', context['pagination_querystring'])

    def test_my_reports_is_paginated(self):
        page = self.client.get('/reports/my_reports/').context['reports']
        self.assertEqual(len(page.object_list), self.per_page)

    def test_projects_list_is_paginated(self):
        response = self.client.get('/projects/')
        self.assertTrue(hasattr(response.context['projects'], 'paginator'))
