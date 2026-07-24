from django.test import TestCase
from django.urls import reverse
from django.contrib.messages import get_messages
from accounts.models import User
from projects.models import Project
from reports.models import Report
from comments.models import Comment
import rules.views as rules

class CommentPermissionTests(TestCase):
    def setUp(self):
        # Create project owner
        self.owner = User.objects.create_user(username='owner', email='owner@example.com', password='password')
        self.owner.is_email_verified = True
        self.owner.save()

        # Create commenter
        self.commenter = User.objects.create_user(username='commenter', email='commenter@example.com', password='password')
        self.commenter.is_email_verified = True
        self.commenter.save()

        # Create other user
        self.other_user = User.objects.create_user(username='other', email='other@example.com', password='password')
        self.other_user.is_email_verified = True
        self.other_user.save()

        # Create project
        self.project = Project.objects.create(
            title="Test Project",
            owner=self.owner,
            visibility="public"
        )

        # Create report
        self.report = Report.objects.create(
            project=self.project,
            reported_by=self.commenter,
            title="Test Report",
            description="Description",
            steps="Steps"
        )

        # Create comment
        self.comment = Comment.objects.create(
            report=self.report,
            commented_by=self.commenter,
            text="Initial comment"
        )

    def test_rules_edit_comment(self):
        """Test rules.can_edit_comment permissions."""
        self.assertTrue(rules.can_edit_comment(self.commenter, self.comment))
        self.assertFalse(rules.can_edit_comment(self.owner, self.comment))
        self.assertFalse(rules.can_edit_comment(self.other_user, self.comment))

    def test_rules_delete_comment(self):
        """Test rules.can_delete_comment permissions."""
        self.assertTrue(rules.can_delete_comment(self.commenter, self.comment))
        self.assertTrue(rules.can_delete_comment(self.owner, self.comment))
        self.assertFalse(rules.can_delete_comment(self.other_user, self.comment))

    def test_edit_comment_view_by_author(self):
        """Test that the commenter can edit their comment via view."""
        self.client.force_login(self.commenter)
        url = reverse('comments:edit_comment', kwargs={'report_uuid': self.report.uuid, 'comment_uuid': self.comment.uuid})
        response = self.client.post(url, {'text': 'Updated comment'})
        self.assertEqual(response.status_code, 200)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.text, 'Updated comment')
        self.assertTrue(self.comment.is_edited)

    def test_edit_comment_view_by_non_author_forbidden(self):
        """Test that a non-author cannot edit a comment."""
        self.client.force_login(self.owner)
        url = reverse('comments:edit_comment', kwargs={'report_uuid': self.report.uuid, 'comment_uuid': self.comment.uuid})
        response = self.client.post(url, {'text': 'Malicious update'})
        self.assertEqual(response.status_code, 403)
        self.comment.refresh_from_db()
        self.assertEqual(self.comment.text, 'Initial comment')

    def test_delete_comment_view_by_author(self):
        """Test that the author can delete their comment."""
        self.client.force_login(self.commenter)
        url = reverse('comments:delete_comment', kwargs={'report_uuid': self.report.uuid, 'comment_uuid': self.comment.uuid})
        # Standard POST request should redirect
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)

        # Re-create comment for HTMX test
        self.comment = Comment.objects.create(
            report=self.report,
            commented_by=self.commenter,
            text="Initial comment"
        )
        url = reverse('comments:delete_comment', kwargs={'report_uuid': self.report.uuid, 'comment_uuid': self.comment.uuid})
        # HTMX request should return 200 empty response
        response = self.client.post(url, HTTP_HX_REQUEST='true')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Comment.objects.filter(uuid=self.comment.uuid).exists())

    def test_delete_comment_view_by_owner(self):
        """Test that the project owner can delete a comment."""
        self.client.force_login(self.owner)
        url = reverse('comments:delete_comment', kwargs={'report_uuid': self.report.uuid, 'comment_uuid': self.comment.uuid})
        # Standard POST request should redirect
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)

        # Re-create comment for HTMX test
        self.comment = Comment.objects.create(
            report=self.report,
            commented_by=self.commenter,
            text="Initial comment"
        )
        url = reverse('comments:delete_comment', kwargs={'report_uuid': self.report.uuid, 'comment_uuid': self.comment.uuid})
        # HTMX request should return 200 empty response
        response = self.client.post(url, HTTP_HX_REQUEST='true')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Comment.objects.filter(uuid=self.comment.uuid).exists())

    def test_delete_comment_view_by_other_user_forbidden(self):
        """Test that other user cannot delete a comment."""
        self.client.force_login(self.other_user)
        url = reverse('comments:delete_comment', kwargs={'report_uuid': self.report.uuid, 'comment_uuid': self.comment.uuid})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Comment.objects.filter(uuid=self.comment.uuid).exists())
