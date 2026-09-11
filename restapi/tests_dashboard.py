"""
Tests for the REST API dashboard and the usage-metrics pipeline.

The dashboard views had no coverage at all and contained three separate 500s:
two unresolvable URL names and one missing template.
"""
import secrets

from django.test import TestCase

from accounts.models import User
from beta.models import UserBetaEnrollment
from organisations.models import Organisation
from projects.models import Project
from restapi.models import ApiKey, ApiKeyScope, ApiRequestLog


def make_user(username, enrol=True):
    user = User.objects.create_user(
        email=f'{username}@example.com', username=username, password='Str0ngPassw!23')
    user.is_email_verified = True
    user.save()
    if enrol:
        UserBetaEnrollment.objects.create(user=user)
    return user


def make_key(user, project, scopes=(('reports', 'read'),)):
    raw_secret = 'rsk_' + secrets.token_hex(32)
    key = ApiKey.objects.create(
        user=user, project=project, name='test key',
        hashed_secret=ApiKey.hash_secret(raw_secret))
    for resource, action in scopes:
        ApiKeyScope.objects.create(api_key=key, resource=resource, action=action)
    return key, raw_secret


class DashboardAccessTests(TestCase):
    def setUp(self):
        self.user = make_user('apidash')
        self.project = Project.objects.create(
            owner=self.user, title='API', link='http://x.com', description='d')
        self.client.force_login(self.user)

    def test_dashboard_renders(self):
        self.assertEqual(self.client.get('/api/dashboard/').status_code, 200)

    def test_unenrolled_user_is_redirected_not_crashed(self):
        UserBetaEnrollment.objects.filter(user=self.user).delete()
        response = self.client.get('/api/dashboard/')
        self.assertEqual(response.status_code, 302)

    def test_key_detail_renders(self):
        key, _ = make_key(self.user, self.project)
        self.assertEqual(self.client.get(f'/api/dashboard/keys/{key.uuid}/').status_code, 200)

    def test_a_users_key_is_not_visible_to_others(self):
        key, _ = make_key(self.user, self.project)
        self.client.force_login(make_user('apidash_other'))
        self.assertEqual(self.client.get(f'/api/dashboard/keys/{key.uuid}/').status_code, 404)


class KeyLifecycleTests(TestCase):
    def setUp(self):
        self.user = make_user('apilife')
        self.project = Project.objects.create(
            owner=self.user, title='API', link='http://x.com', description='d')
        self.client.force_login(self.user)

    def test_create_key(self):
        response = self.client.post('/api/dashboard/keys/create/', {
            'name': 'CI key', 'project_uuid': str(self.project.uuid),
            'scopes': ['reports.read', 'reports.create'],
        })
        self.assertEqual(response.status_code, 200)
        key = ApiKey.objects.get(name='CI key')
        self.assertEqual(key.scopes.count(), 2)
        # The raw secret is shown exactly once and never stored.
        self.assertIn('rsk_', response.content.decode())
        self.assertNotIn(response.context['raw_secret'], key.hashed_secret)

    def test_create_key_rejects_an_unknown_scope(self):
        self.client.post('/api/dashboard/keys/create/', {
            'name': 'Bad scope', 'project_uuid': str(self.project.uuid),
            'scopes': ['reports.read', 'reports.launch_missiles'],
        })
        key = ApiKey.objects.get(name='Bad scope')
        self.assertEqual(
            list(key.scopes.values_list('resource', 'action')), [('reports', 'read')])

    def test_create_key_for_a_foreign_project_is_refused(self):
        foreign = Project.objects.create(
            owner=make_user('apilife_other', enrol=False), title='Theirs',
            link='http://x.com', description='d', visibility='private', public=False)
        response = self.client.post('/api/dashboard/keys/create/', {
            'name': 'Sneaky', 'project_uuid': str(foreign.uuid), 'scopes': ['reports.read'],
        })
        self.assertEqual(response.status_code, 302)
        self.assertFalse(ApiKey.objects.filter(project=foreign).exists())

    def test_malformed_project_uuid_does_not_500(self):
        response = self.client.post('/api/dashboard/keys/create/', {
            'name': 'Junk', 'project_uuid': 'not-a-uuid', 'scopes': ['reports.read'],
        })
        self.assertEqual(response.status_code, 302)

    def test_org_member_can_create_a_key_for_an_org_project(self):
        org_owner = make_user('apilife_orgowner')
        org = Organisation.objects.create(name='API Org', owner=org_owner)
        org.members.add(self.user)
        org_project = Project.objects.create(
            owner=org_owner, title='Org API', link='http://x.com', description='d', org=org)

        # The dashboard offers it…
        listed = self.client.get('/api/dashboard/').context['projects']
        self.assertIn(org_project, listed)
        # …so creation must accept it.
        self.client.post('/api/dashboard/keys/create/', {
            'name': 'Org key', 'project_uuid': str(org_project.uuid), 'scopes': ['reports.read'],
        })
        self.assertTrue(ApiKey.objects.filter(name='Org key', project=org_project).exists())

    def test_revoke_over_htmx_returns_the_row(self):
        key, _ = make_key(self.user, self.project)
        response = self.client.post(
            f'/api/dashboard/keys/{key.uuid}/revoke/', HTTP_HX_REQUEST='true')
        self.assertEqual(response.status_code, 200)
        self.assertIn(f'api-key-row-{key.uuid}', response.content.decode())
        key.refresh_from_db()
        self.assertEqual(key.status, 'revoked')

    def test_delete_over_htmx_swaps_the_row_away(self):
        key, _ = make_key(self.user, self.project)
        response = self.client.post(
            f'/api/dashboard/keys/{key.uuid}/delete/', HTTP_HX_REQUEST='true')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'')
        self.assertFalse(ApiKey.objects.filter(uuid=key.uuid).exists())

    def test_active_key_count_is_capped(self):
        from restapi.dashboard_views import MAX_ACTIVE_KEYS_PER_USER

        for i in range(MAX_ACTIVE_KEYS_PER_USER):
            make_key(self.user, self.project)
        self.client.post('/api/dashboard/keys/create/', {
            'name': 'One too many', 'project_uuid': str(self.project.uuid),
            'scopes': ['reports.read'],
        })
        self.assertFalse(ApiKey.objects.filter(name='One too many').exists())


class UsageMetricsTests(TestCase):
    """BETA-04 — the metrics dashboard must reflect what actually happened."""

    def setUp(self):
        self.user = make_user('apimetrics')
        self.project = Project.objects.create(
            owner=self.user, title='API', link='http://x.com', description='d')
        self.key, self.secret = make_key(
            self.user, self.project, scopes=(('reports', 'read'), ('reports', 'create')))
        self.auth = f'Bearer {self.key.public_key}:{self.secret}'

    def test_a_failed_request_is_logged_with_its_real_status(self):
        response = self.client.post(
            '/api/v1/reports/', data='{"title": ""}', content_type='application/json',
            HTTP_AUTHORIZATION=self.auth)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            list(ApiRequestLog.objects.filter(api_key=self.key).values_list('status_code', flat=True)),
            [400],
        )

    def test_a_created_report_is_logged_as_201(self):
        response = self.client.post(
            '/api/v1/reports/',
            data='{"title": "Via API", "description": "d", "steps": "s"}',
            content_type='application/json', HTTP_AUTHORIZATION=self.auth)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            ApiRequestLog.objects.filter(api_key=self.key, status_code=201).count(), 1)

    def test_unauthenticated_failures_do_not_write_log_rows(self):
        """SEC-09 — a public key is not a secret; it must not be a write primitive."""
        for _ in range(5):
            self.client.get(
                '/api/v1/reports/',
                HTTP_AUTHORIZATION=f'Bearer {self.key.public_key}:rsk_wrong')
        self.assertEqual(ApiRequestLog.objects.filter(api_key=self.key).count(), 0)

    def test_repeated_bad_secrets_are_throttled(self):
        from django.core.cache import cache
        from restapi.auth import AUTH_FAILURE_LIMIT

        cache.clear()
        statuses = [
            self.client.get(
                '/api/v1/reports/',
                HTTP_AUTHORIZATION=f'Bearer {self.key.public_key}:rsk_wrong').status_code
            for _ in range(AUTH_FAILURE_LIMIT + 4)
        ]
        self.assertIn(429, statuses, 'brute-forcing a secret must eventually be throttled')
        cache.clear()

    def test_key_detail_metrics_render(self):
        self.client.get('/api/v1/reports/', HTTP_AUTHORIZATION=self.auth)
        self.client.force_login(self.user)
        context = self.client.get(f'/api/dashboard/keys/{self.key.uuid}/').context
        self.assertEqual(context['total_30d'], 1)
        self.assertEqual(context['success_30d'], 1)
        self.assertEqual(context['error_30d'], 0)
        self.assertEqual(len(context['daily_counts']), 14)


class ListPaginationTests(TestCase):
    def setUp(self):
        self.user = make_user('apipage')
        self.project = Project.objects.create(
            owner=self.user, title='API', link='http://x.com', description='d')
        self.key, self.secret = make_key(self.user, self.project)
        self.auth = f'Bearer {self.key.public_key}:{self.secret}'
        from reports.models import Report
        for i in range(12):
            Report.objects.create(
                title=f'Report {i}', project=self.project, reported_by=self.user,
                description='d', steps='s')

    def _get(self, query=''):
        return self.client.get(f'/api/v1/reports/{query}', HTTP_AUTHORIZATION=self.auth)

    def test_response_reports_the_total(self):
        body = self._get().json()
        self.assertEqual(body['count'], 12)
        self.assertEqual(len(body['results']), 12)

    def test_limit_and_offset(self):
        first = self._get('?limit=5').json()
        second = self._get('?limit=5&offset=5').json()
        self.assertEqual(len(first['results']), 5)
        self.assertEqual(len(second['results']), 5)
        self.assertNotEqual(
            [r['uuid'] for r in first['results']], [r['uuid'] for r in second['results']])

    def test_limit_is_bounded(self):
        self.assertEqual(self._get('?limit=100000').status_code, 400)
        self.assertEqual(self._get('?limit=0').status_code, 400)
        self.assertEqual(self._get('?offset=-1').status_code, 400)
        self.assertEqual(self._get('?limit=abc').status_code, 400)


class ScopeMatrixTests(TestCase):
    """BETA-03 — the UI must not advertise permissions no endpoint honours."""

    def test_every_offered_scope_is_implemented(self):
        from restapi.dashboard_views import RETIRED_SCOPES, SCOPE_MATRIX

        offered = {(resource, action)
                   for resource, _, actions in SCOPE_MATRIX for action in actions}
        self.assertEqual(offered, {('reports', 'read'), ('reports', 'create')})
        self.assertFalse(offered & RETIRED_SCOPES)
