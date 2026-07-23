from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from projects.models import Project
from reports.models import Report
from notifications.models import Invitation
import base64

User = get_user_model()

class AuthenticationEmailTests(TestCase):
    def setUp(self):
        # Create a verified user
        self.verified_user = User.objects.create_user(
            username='verified',
            email='verified@example.com',
            password='Password123!',
            is_email_verified=True
        )
        # Create an unverified user
        self.unverified_user = User.objects.create_user(
            username='unverified',
            email='unverified@example.com',
            password='Password123!',
            is_email_verified=False
        )
        # Create a project
        self.project = Project.objects.create(
            owner=self.verified_user,
            title="Verified Project",
            visibility="public"
        )
        # Create a report
        self.report = Report.objects.create(
            project=self.project,
            reported_by=self.verified_user,
            title="Verified Report",
            description="Verified Description",
            steps="Steps"
        )

    def test_signup_initializes_unverified(self):
        """Test that registering a new account defaults to unverified."""
        response = self.client.post(
            reverse('home:handle_signup'),
            {
                'email': 'newuser@example.com',
                'password': 'Password123!',
                'confirm_password': 'Password123!',
                'accept_terms': 'on'
            }
        )
        self.assertEqual(response.status_code, 204) # HX-Redirect triggered
        new_user = User.objects.get(email='newuser@example.com')
        self.assertFalse(new_user.is_email_verified)

    def test_signup_fails_without_accepting_terms(self):
        """Test that signup fails if the user does not accept terms and conditions."""
        response = self.client.post(
            reverse('home:handle_signup'),
            {
                'email': 'newuser_no_terms@example.com',
                'password': 'Password123!',
                'confirm_password': 'Password123!'
            }
        )
        self.assertEqual(response.status_code, 200) # Form re-renders with error
        self.assertIn('You must accept the Terms & Conditions and Privacy Policy to register.', response.content.decode('utf-8'))
        self.assertFalse(User.objects.filter(email='newuser_no_terms@example.com').exists())

    def test_verify_email_endpoint(self):
        """Test token-based email verification view sets flag to True."""
        user = self.unverified_user
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        
        response = self.client.get(
            reverse('accounts:verify_email', kwargs={'uidb64': uidb64, 'token': token})
        )
        self.assertRedirects(response, reverse('home:landing_page'))
        user.refresh_from_db()
        self.assertTrue(user.is_email_verified)

    def test_unverified_user_blocked_actions(self):
        """Test unverified users cannot perform state-modifying actions."""
        self.client.force_login(self.unverified_user)

        # 1. Block Project Creation
        response = self.client.post(
            reverse('projects:new'),
            {'title': 'New Proj', 'visibility': 'public', 'components-TOTAL_FORMS': '0', 'components-INITIAL_FORMS': '0'}
        )
        self.assertContains(response, "Email Verification Required")
        self.assertContains(response, "Verify your email to create projects.")

        # 2. Block Report Creation
        response = self.client.post(
            reverse('reports:new'),
            {'title': 'New Report', 'description': 'desc', 'steps': 'steps'}
        )
        self.assertContains(response, "Email Verification Required")
        self.assertContains(response, "Verify your email to create reports.")

        # 3. Block Comment Creation (inline HTMX partial)
        response = self.client.post(
            reverse('comments:add_comment', kwargs={'report_uuid': self.report.uuid}),
            {'content': 'Test Comment'}
        )
        self.assertContains(response, "Verify your email to leave comments.")
        self.assertContains(response, "Resend verification email")

    def test_change_email_confirmation_flow(self):
        """Test profile edit triggers pending email confirmation flow rather than direct update."""
        self.client.force_login(self.verified_user)
        
        response = self.client.post(
            reverse('accounts:edit_profile'),
            {
                'name': 'New Verified Name',
                'username': 'verified_updated',
                'email': 'new_pending@example.com',
                'github_link': ''
            }
        )
        self.assertRedirects(response, reverse('home:profile'))
        
        self.verified_user.refresh_from_db()
        # Primary email remains unchanged
        self.assertEqual(self.verified_user.email, 'verified@example.com')
        # Pending email stored
        self.assertEqual(self.verified_user.pending_email, 'new_pending@example.com')

        # Now confirm email change
        uidb64 = urlsafe_base64_encode(force_bytes(self.verified_user.pk))
        token = default_token_generator.make_token(self.verified_user)
        new_email_b64 = base64.urlsafe_b64encode(b'new_pending@example.com').decode('utf-8')

        response = self.client.get(
            reverse('accounts:confirm_email_change', kwargs={
                'uidb64': uidb64,
                'token': token,
                'new_email_b64': new_email_b64
            })
        )
        self.assertRedirects(response, reverse('home:profile'))
        
        self.verified_user.refresh_from_db()
        self.assertEqual(self.verified_user.email, 'new_pending@example.com')
        self.assertIsNone(self.verified_user.pending_email)
