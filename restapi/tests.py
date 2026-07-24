import json
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from accounts.models import User
from projects.models import Project
from restapi.models import ApiKey, ApiKeyScope
from beta.models import UserBetaEnrollment, BetaFeature

User = get_user_model()


class RestApiTests(TestCase):

    def setUp(self):
        # Create users
        self.owner = User.objects.create_user(
            username='project_owner',
            email='owner@example.com',
            password='password123'
        )
        self.reporter = User.objects.create_user(
            username='reporter_user',
            email='reporter@example.com',
            password='password123'
        )

        # Enroll reporter in beta to allow API access
        self.feature_api, _ = BetaFeature.objects.get_or_create(
            slug='rest_api',
            defaults={
                'name': 'REST API & API Keys',
                'description': 'API',
                'status': 'beta'
            }
        )
        UserBetaEnrollment.objects.create(user=self.reporter)

        # Create project
        self.project = Project.objects.create(
            title="API Sandbox",
            owner=self.owner
        )

        # Create API key for reporter
        self.raw_secret = 'rsk_very_secret_key_12345'
        self.api_key = ApiKey.objects.create(
            user=self.reporter,
            project=self.project,
            name="Test Token",
            hashed_secret=ApiKey.hash_secret(self.raw_secret),
            is_active=True
        )

        # Assign scopes
        ApiKeyScope.objects.create(api_key=self.api_key, resource='reports', action='create')
        ApiKeyScope.objects.create(api_key=self.api_key, resource='reports', action='read')

    def test_api_auth_success(self):
        """Valid Bearer credentials with correct scopes succeed."""
        url = reverse('api_v1:reports')
        auth_header = f"Bearer {self.api_key.public_key}:{self.raw_secret}"

        # GET reports list
        response = self.client.get(
            url,
            HTTP_AUTHORIZATION=auth_header
        )
        self.assertEqual(response.status_code, 200)

    def test_api_auth_invalid_secret(self):
        """Invalid secret key fails authentication."""
        url = reverse('api_v1:reports')
        auth_header = f"Bearer {self.api_key.public_key}:wrong_secret"

        response = self.client.get(
            url,
            HTTP_AUTHORIZATION=auth_header
        )
        self.assertEqual(response.status_code, 401)

    def test_api_auth_missing_scope(self):
        """A request lacking scope permissions fails with 403."""
        # Create a new key with no scopes
        no_scope_key = ApiKey.objects.create(
            user=self.reporter,
            project=self.project,
            name="No Scopes Token",
            hashed_secret=ApiKey.hash_secret(self.raw_secret),
            is_active=True
        )
        auth_header = f"Bearer {no_scope_key.public_key}:{self.raw_secret}"
        url = reverse('api_v1:reports')

        response = self.client.get(
            url,
            HTTP_AUTHORIZATION=auth_header
        )
        self.assertEqual(response.status_code, 403)

    def test_create_report_via_api(self):
        """POST /api/v1/reports/ successfully creates a report."""
        url = reverse('api_v1:reports')
        auth_header = f"Bearer {self.api_key.public_key}:{self.raw_secret}"

        payload = {
            "title": "API Bug Report",
            "description": "Found a bug using API client.",
            "impact": "medium",
            "frequency": "daily"
        }

        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_AUTHORIZATION=auth_header
        )
        self.assertEqual(response.status_code, 201)

        # Verify report was created in DB
        data = response.json()
        self.assertIn('uuid', data)
        self.assertEqual(data['title'], "API Bug Report")
        self.assertEqual(data['project'], str(self.project.uuid))

    def test_create_report_invalid_payload(self):
        """POST /api/v1/reports/ with invalid fields fails validation with 400."""
        url = reverse('api_v1:reports')
        auth_header = f"Bearer {self.api_key.public_key}:{self.raw_secret}"

        # Missing required title and description
        payload = {
            "impact": "invalid_value",
        }

        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_AUTHORIZATION=auth_header
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn('error', response.json())

    def test_create_duplicate_report_via_api(self):
        """POST /api/v1/reports/ rejects duplicate titles in the same project with 400."""
        url = reverse('api_v1:reports')
        auth_header = f"Bearer {self.api_key.public_key}:{self.raw_secret}"

        payload = {
            "title": "Unique API Bug",
            "description": "desc",
        }

        # First post succeeds
        response1 = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_AUTHORIZATION=auth_header
        )
        self.assertEqual(response1.status_code, 201)

        # Second post with identical title fails
        response2 = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json',
            HTTP_AUTHORIZATION=auth_header
        )
        self.assertEqual(response2.status_code, 400)
        self.assertIn("A report with this title already exists for this project.", response2.json()['error'])

