from django.test import TestCase
from django.contrib.auth import get_user_model
from accounts.models import User
from projects.models import Project
from organisations.models import Organisation
from beta.models import BetaFeature, UserBetaEnrollment, OrgBetaEnrollment
from beta.utils import user_has_feature

User = get_user_model()


class BetaProgramTests(TestCase):

    def setUp(self):
        # Create users
        self.user_owner = User.objects.create_user(
            username='owner_user',
            email='owner@example.com',
            password='password123'
        )
        self.user_member = User.objects.create_user(
            username='member_user',
            email='member@example.com',
            password='password123'
        )
        self.other_user = User.objects.create_user(
            username='other_user',
            email='other@example.com',
            password='password123'
        )

        # Create organisation
        self.org = Organisation.objects.create(
            name="Test Org",
            owner=self.user_owner
        )
        self.org.members.add(self.user_member)

        # Create projects
        self.org_project = Project.objects.create(
            title="Org Project",
            owner=self.user_member,
            org=self.org
        )
        self.personal_project = Project.objects.create(
            title="Personal Project",
            owner=self.user_member,
            org=None
        )

        # Create beta features
        self.feature_beta = BetaFeature.objects.create(
            slug='beta_test_feature',
            name='Beta Test Feature',
            description='A feature in beta stage.',
            status='beta'
        )
        self.feature_stable = BetaFeature.objects.create(
            slug='stable_test_feature',
            name='Stable Test Feature',
            description='A graduated stable feature.',
            status='stable'
        )

    def test_stable_feature_always_accessible(self):
        """Graduated stable features must be accessible to everyone immediately."""
        self.assertTrue(user_has_feature(self.user_member, 'stable_test_feature'))
        self.assertTrue(user_has_feature(self.other_user, 'stable_test_feature'))
        self.assertTrue(user_has_feature(self.user_member, 'stable_test_feature', project=self.personal_project))

    def test_unenroll_user_cannot_access_beta_feature(self):
        """Unenrolled users must not have access to beta features."""
        self.assertFalse(user_has_feature(self.user_member, 'beta_test_feature'))
        self.assertFalse(user_has_feature(self.user_member, 'beta_test_feature', project=self.personal_project))

    def test_enrolled_user_access(self):
        """Enrolled users get access to beta features."""
        UserBetaEnrollment.objects.create(user=self.user_member)
        self.assertTrue(user_has_feature(self.user_member, 'beta_test_feature'))
        self.assertTrue(user_has_feature(self.user_member, 'beta_test_feature', project=self.personal_project))

    def test_org_enrollment_scopes_to_org_projects_only(self):
        """
        When an org is enrolled:
        - Org members can use beta features on that org's projects.
        - Org members cannot use beta features on personal projects (unless personally enrolled).
        """
        # Enroll the organisation
        OrgBetaEnrollment.objects.create(org=self.org, enrolled_by=self.user_owner)

        # User member is not personally enrolled
        # 1. Access on org project -> True
        self.assertTrue(user_has_feature(self.user_member, 'beta_test_feature', project=self.org_project))
        
        # 2. Access on personal project -> False
        self.assertFalse(user_has_feature(self.user_member, 'beta_test_feature', project=self.personal_project))

        # 3. Access in general (no project context) -> False
        self.assertFalse(user_has_feature(self.user_member, 'beta_test_feature'))


class BetaGateRegressionTests(TestCase):
    """Regressions for SEC-11, PERF-01 and BETA-01/BETA-02."""

    def setUp(self):
        from beta.utils import invalidate_feature_registry
        invalidate_feature_registry()

        self.user = User.objects.create_user(
            username='gate_user', email='gate@example.com', password='password123')
        self.org_owner = User.objects.create_user(
            username='gate_org_owner', email='gateorg@example.com', password='password123')
        self.org_member = User.objects.create_user(
            username='gate_org_member', email='gatemember@example.com', password='password123')

        self.hidden = BetaFeature.objects.create(
            slug='internal_kill_switch', name='Internal', description='hidden',
            status='beta', is_enrollable=False)
        self.visible = BetaFeature.objects.create(
            slug='public_beta_feature', name='Public Beta', description='shown',
            status='beta', is_enrollable=True)

    def tearDown(self):
        from beta.utils import invalidate_feature_registry
        invalidate_feature_registry()

    # ── SEC-11 ────────────────────────────────────────────────────────────────
    def test_blanket_enrollment_excludes_non_enrollable_features(self):
        UserBetaEnrollment.objects.create(user=self.user)
        self.assertTrue(user_has_feature(self.user, 'public_beta_feature'))
        self.assertFalse(
            user_has_feature(self.user, 'internal_kill_switch'),
            "is_enrollable=False must keep a feature out of the blanket grant",
        )

    def test_non_enrollable_feature_is_absent_from_the_features_dict(self):
        from beta.utils import get_user_beta_features
        UserBetaEnrollment.objects.create(user=self.user)
        self.assertNotIn('internal_kill_switch', get_user_beta_features(self.user))

    def test_explicit_enrollment_in_a_hidden_feature_is_still_honoured(self):
        enrollment = UserBetaEnrollment.objects.create(user=self.user)
        enrollment.features.add(self.hidden)
        self.assertTrue(user_has_feature(self.user, 'internal_kill_switch'))

    def test_org_blanket_enrollment_excludes_non_enrollable_features(self):
        org = Organisation.objects.create(name='Gate Org', owner=self.org_owner)
        project = Project.objects.create(title='Gate Project', owner=self.org_owner, org=org)
        OrgBetaEnrollment.objects.create(org=org, enrolled_by=self.org_owner)

        from beta.utils import project_has_feature
        self.assertTrue(project_has_feature(project, 'public_beta_feature'))
        self.assertFalse(project_has_feature(project, 'internal_kill_switch'))

    # ── PERF-01 ───────────────────────────────────────────────────────────────
    def test_context_processor_query_budget(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        from beta.context_processors import beta_features

        UserBetaEnrollment.objects.create(user=self.user)
        request = type('R', (), {'user': self.user})()

        beta_features(request)  # warm the registry cache
        with CaptureQueriesContext(connection) as ctx:
            beta_features(request)

        self.assertLessEqual(
            len(ctx.captured_queries), 3,
            f"beta_features runs on every page render; it used "
            f"{len(ctx.captured_queries)} queries:\n"
            + "\n".join(q['sql'][:120] for q in ctx.captured_queries),
        )

    def test_registry_cache_is_invalidated_when_a_feature_changes(self):
        from beta.utils import get_feature_registry
        self.assertEqual(get_feature_registry()['public_beta_feature']['status'], 'beta')
        self.visible.status = 'stable'
        self.visible.save()
        self.assertEqual(get_feature_registry()['public_beta_feature']['status'], 'stable')
        self.assertTrue(user_has_feature(self.org_member, 'public_beta_feature'))

    # ── BETA-01 ───────────────────────────────────────────────────────────────
    def test_non_htmx_enroll_and_unenroll_redirect_instead_of_crashing(self):
        self.client.force_login(self.user)

        response = self.client.post('/beta/enroll/')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(UserBetaEnrollment.objects.filter(user=self.user).exists())

        response = self.client.post('/beta/unenroll/')
        self.assertEqual(response.status_code, 302)
        self.assertFalse(UserBetaEnrollment.objects.filter(user=self.user).exists())

    def test_non_htmx_org_enroll_redirects_instead_of_crashing(self):
        org = Organisation.objects.create(name='Redirect Org', owner=self.org_owner)
        self.client.force_login(self.org_owner)

        response = self.client.post(f'/beta/org/{org.uuid}/enroll/')
        self.assertEqual(response.status_code, 302)
        self.assertTrue(OrgBetaEnrollment.objects.filter(org=org).exists())

    # ── BETA-02 ───────────────────────────────────────────────────────────────
    def test_org_members_are_notified_on_enrollment(self):
        from notifications.models import Notification

        org = Organisation.objects.create(name='Notify Org', owner=self.org_owner)
        org.members.add(self.org_member)
        self.client.force_login(self.org_owner)

        self.client.post(f'/beta/org/{org.uuid}/enroll/', HTTP_HX_REQUEST='true')

        notification = Notification.objects.filter(
            recipient=self.org_member, notification_type='beta_enrollment').first()
        self.assertIsNotNone(notification, "org members must actually receive the announcement")
        self.assertEqual(notification.target_content_type, 'organisation')
        self.assertEqual(notification.target_uuid, org.uuid)

    def test_unknown_notification_type_is_rejected(self):
        from notifications.services import create_notification
        with self.assertRaises(ValueError):
            create_notification(
                recipient=self.user, actor=self.org_owner,
                notification_type='new_report', title='t', message='m',
                target_content_type=None, target_uuid=None,
            )
