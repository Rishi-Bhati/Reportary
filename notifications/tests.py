from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from projects.models import Project
from organisations.models import Organisation
from reports.models import Report
from .models import Notification, Invitation
from .services import (
    create_notification,
    create_invitation,
    accept_invitation,
    decline_invitation,
    get_unread_count
)

User = get_user_model()

class NotificationSystemTests(TestCase):
    def setUp(self):
        # Create users
        self.owner = User.objects.create_user(
            username='project_owner',
            email='owner@example.com',
            password='Password123!'
        )
        self.developer = User.objects.create_user(
            username='dev_user',
            email='dev@example.com',
            password='Password123!'
        )
        
        # Create project
        self.project = Project.objects.create(
            owner=self.owner,
            title="Test Project",
            link="http://example.com",
            description="A test project.",
            visibility="public"
        )
        self.project.collaborators.add(self.owner)

        # Create organisation
        self.org = Organisation.objects.create(
            owner=self.owner,
            name="Test Org",
            description="A test org."
        )

    def test_create_notification(self):
        """Test creating informational in-app notifications."""
        notif = create_notification(
            recipient=self.developer,
            actor=self.owner,
            notification_type='report_assigned',
            title="Test Notification",
            message="This is a test notification.",
            target_content_type='project',
            target_uuid=self.project.uuid
        )
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(notif.recipient, self.developer)
        self.assertEqual(notif.actor, self.owner)
        self.assertFalse(notif.is_read)
        self.assertFalse(notif.requires_action)

    def test_create_invitation(self):
        """Test creating collaboration invitation."""
        invite = create_invitation(
            invite_type='collaborator',
            invited_by=self.owner,
            invited_user=self.developer,
            project=self.project
        )
        self.assertEqual(Invitation.objects.count(), 1)
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(invite.status, 'pending')
        self.assertEqual(invite.notification.recipient, self.developer)
        self.assertTrue(invite.notification.requires_action)

    def test_accept_collaborator_invitation(self):
        """Test accepting collaboration invitation."""
        invite = create_invitation(
            invite_type='collaborator',
            invited_by=self.owner,
            invited_user=self.developer,
            project=self.project
        )
        
        # Accept invite
        accept_invitation(invite, self.developer)
        invite.refresh_from_db()
        
        self.assertEqual(invite.status, 'accepted')
        self.assertTrue(invite.notification.is_read)
        self.assertTrue(self.project.collaborators.filter(id=self.developer.id).exists())

    def test_decline_collaborator_invitation(self):
        """Test declining collaboration invitation."""
        invite = create_invitation(
            invite_type='collaborator',
            invited_by=self.owner,
            invited_user=self.developer,
            project=self.project
        )
        
        # Decline invite
        decline_invitation(invite, self.developer)
        invite.refresh_from_db()
        
        self.assertEqual(invite.status, 'declined')
        self.assertTrue(invite.notification.is_read)
        self.assertFalse(self.project.collaborators.filter(id=self.developer.id).exists())

    def test_accept_org_invitation(self):
        """Test accepting organisation membership invitation."""
        invite = create_invitation(
            invite_type='organisation',
            invited_by=self.owner,
            invited_user=self.developer,
            organisation=self.org
        )
        
        # Accept invite
        accept_invitation(invite, self.developer)
        invite.refresh_from_db()
        
        self.assertEqual(invite.status, 'accepted')
        self.assertTrue(self.org.members.filter(id=self.developer.id).exists())

    def test_notification_center_view(self):
        """Test notification center view gets rendered and auto-marks non-actionable as read."""
        create_notification(
            recipient=self.developer,
            actor=self.owner,
            notification_type='report_assigned',
            title="Test Title",
            message="Test Msg",
            target_content_type='project',
            target_uuid=self.project.uuid
        )
        
        self.client.login(email='dev@example.com', password='Password123!')
        response = self.client.get(reverse('notifications:center'))
        self.assertEqual(response.status_code, 200)
        
        # Auto-mark read should have run on loading the center
        self.assertEqual(get_unread_count(self.developer), 0)


class AnnouncementNotificationTests(TestCase):
    def setUp(self):
        from core.models import Announcement
        self.user = User.objects.create_user(
            username='dev_user',
            email='dev@example.com',
            password='Password123!'
        )
        self.announcement = Announcement.objects.create(
            title="System Maintenance",
            body="Planned downtime tonight.",
            level="info",
            is_active=True
        )

    def test_announcement_visibility_and_dismissal(self):
        """Active announcements show in context, but not after user dismisses them."""
        self.client.login(email='dev@example.com', password='Password123!')
        
        # 1. Shows initially
        response1 = self.client.get(reverse('dashboard:dashboard'))
        self.assertEqual(response1.status_code, 200)
        self.assertIn(self.announcement, response1.context['site_announcements'])

        # 2. Dismiss via POST
        url = reverse('dismiss_announcement', kwargs={'announcement_id': self.announcement.id})
        response_dismiss = self.client.post(url)
        self.assertEqual(response_dismiss.status_code, 200)

        # 3. Excluded from next visits
        response2 = self.client.get(reverse('dashboard:dashboard'))
        self.assertEqual(response2.status_code, 200)
        self.assertNotIn(self.announcement, response2.context['site_announcements'])

    def test_announcements_in_notification_center(self):
        """Notification center displays announcements and dismissal state."""
        self.client.login(email='dev@example.com', password='Password123!')

        # 1. Tab displays the announcement as undismissed
        url = reverse('notifications:center') + "?tab=announcements"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['announcements_count'], 1)
        ann_list = resp.context['announcements_list']
        self.assertEqual(len(ann_list), 1)
        self.assertFalse(ann_list[0].is_dismissed)

        # 2. Dismiss the announcement
        dismiss_url = reverse('dismiss_announcement', kwargs={'announcement_id': self.announcement.id})
        self.client.post(dismiss_url)

        # 3. Tab displays the announcement as dismissed and count is 0
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['announcements_count'], 0)
        ann_list = resp.context['announcements_list']
        self.assertEqual(len(ann_list), 1)
        self.assertTrue(ann_list[0].is_dismissed)

