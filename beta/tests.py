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
