from django.test import TestCase
from django.urls import reverse
from accounts.models import User
from projects.models import Project
from reports.models import Report


class ReportListTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', email='owner@example.com', password='password')
        self.reporter = User.objects.create_user(username='reporter', email='reporter@example.com', password='password')
        self.other = User.objects.create_user(username='other', email='other@example.com', password='password')

        self.project = Project.objects.create(title='Project A', link='https://example.com', description='desc', owner=self.owner)

        # Visible report by reporter
        self.visible_report = Report.objects.create(project=self.project, title='Visible', description='vis', reported_by=self.reporter, visibility=True)
        # Hidden report by reporter
        self.hidden_report = Report.objects.create(project=self.project, title='Hidden', description='hid', reported_by=self.reporter, visibility=False)

    def test_anonymous_sees_visible_only(self):
        url = reverse('projects:reports:report_list', kwargs={'project_uuid': self.project.uuid})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        reports = resp.context['reports']
        self.assertIn(self.visible_report, reports)
        self.assertNotIn(self.hidden_report, reports)

    def test_owner_sees_all_reports(self):
        self.client.force_login(self.owner)
        url = reverse('projects:reports:report_list', kwargs={'project_uuid': self.project.uuid})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        reports = resp.context['reports']
        self.assertIn(self.visible_report, reports)
        self.assertIn(self.hidden_report, reports)

    def test_reporter_sees_their_hidden_report(self):
        self.client.force_login(self.reporter)
        url = reverse('projects:reports:report_list', kwargs={'project_uuid': self.project.uuid})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        reports = resp.context['reports']
        self.assertIn(self.visible_report, reports)
        self.assertIn(self.hidden_report, reports)

    def test_root_reports_redirects(self):
        self.client.force_login(self.reporter)
        url = reverse('reports:report_list')
        resp = self.client.get(url)
        self.assertRedirects(resp, reverse('reports:my_reports'))


class ReportDetailTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='report_owner', email='report_owner@example.com', password='password')
        self.collaborator = User.objects.create_user(username='collab', email='collab@example.com', password='password')
        
        self.project = Project.objects.create(title='Project A', link='https://example.com', description='desc', owner=self.owner)
        self.project.collaborators.add(self.collaborator)
        
        self.report = Report.objects.create(
            project=self.project, 
            title='Report 1', 
            description='desc', 
            reported_by=self.owner,
            visibility=True
        )

    def test_collaborators_in_context(self):
        self.client.force_login(self.owner)
        url = reverse('projects:reports:report_detail', kwargs={'project_uuid': self.project.uuid, 'report_uuid': self.report.uuid})
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        
        # Check if collaborators are correctly passed to context
        collaborators = resp.context['collaborators']
        
        self.assertIn(self.collaborator, collaborators)

class ReportsSearchAndNeedsAttentionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', email='testuser@example.com', password='password')
        self.user2 = User.objects.create_user(username='user2', email='user2@example.com', password='password')
        
        self.project_owned = Project.objects.create(title='Owned Project', link='https://example.com', description='desc', owner=self.user)
        self.project_other = Project.objects.create(title='Other Project', link='https://example.com', description='desc', owner=self.user2)
        self.project_other.collaborators.add(self.user)
        
        # Reports
        self.critical_assigned = Report.objects.create(project=self.project_other, title='Critical assigned', severity='critical', assigned_to=self.user, reported_by=self.user2, visibility=True)
        self.critical_on_my_project = Report.objects.create(project=self.project_owned, title='Critical on owned', severity='critical', reported_by=self.user2, visibility=True)
        self.normal_report = Report.objects.create(project=self.project_owned, title='Normal report', severity='medium', reported_by=self.user2, visibility=True)

    def test_my_reports_search(self):
        self.client.force_login(self.user)
        # Create a report created by self.user
        my_rep = Report.objects.create(project=self.project_owned, title='My Special Report', severity='low', reported_by=self.user, visibility=True)
        
        url = reverse('reports:my_reports')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.context['reports']), 1)
        self.assertEqual(resp.context['reports'][0], my_rep)
        
        resp = self.client.get(url + '?q=Special')
        self.assertEqual(len(resp.context['reports']), 1)
        
        resp = self.client.get(url + '?q=NonExistent')
        self.assertEqual(len(resp.context['reports']), 0)

    def test_needs_attention(self):
        self.client.force_login(self.user)
        url = reverse('reports:needs_attention')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        
        # Needs attention should include critical assigned and critical on user's projects, but not normal severity reports
        reports = resp.context['reports']
        self.assertEqual(len(reports), 2)
        self.assertIn(self.critical_assigned, reports)
        self.assertIn(self.critical_on_my_project, reports)
        self.assertNotIn(self.normal_report, reports)


class ReportWorkflowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='reporter_user', email='rep@example.com', password='password', is_email_verified=True)
        self.other_user = User.objects.create_user(username='other_user', email='other@example.com', password='password', is_email_verified=True)
        
        self.project = Project.objects.create(title='Workflow Project', link='https://example.com', description='desc', owner=self.user)
        
        # Reports
        self.critical_assigned = Report.objects.create(project=self.project, title='Critical assigned', severity='critical', assigned_to=self.user, reported_by=self.user, visibility=True)
        self.normal_report = Report.objects.create(project=self.project, title='Normal Report', severity='medium', reported_by=self.user, visibility=True)

    def test_edit_report_permissions(self):
        # User who reported can edit
        self.client.force_login(self.user)
        url = reverse('projects:reports:edit_report', kwargs={'project_uuid': self.project.uuid, 'report_uuid': self.critical_assigned.uuid})
        
        # GET form
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        
        # POST edit
        data = {
            'title': 'Updated Title',
            'description': 'Updated Description',
            'steps': 'Updated Steps',
            'frequency': 'daily',
            'impact': 'high',
            'visibility': True,
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302)
        self.critical_assigned.refresh_from_db()
        self.assertEqual(self.critical_assigned.title, 'Updated Title')
        
        # Stranger cannot edit (other_user)
        self.client.force_login(self.other_user)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 403)
        
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 403)

        # Collaborator (who is not assignee or reporter) cannot edit
        collaborator = User.objects.create_user(username='collab_user', email='collab@example.com', password='password', is_email_verified=True)
        self.project.collaborators.add(collaborator)
        self.client.force_login(collaborator)
        
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 403)
        
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 403)

    def test_delete_report_permissions(self):
        # Author can delete
        self.client.force_login(self.user)
        url = reverse('projects:reports:delete_report', kwargs={'project_uuid': self.project.uuid, 'report_uuid': self.critical_assigned.uuid})
        
        # GET confirm modal
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        
        # Stranger cannot delete
        self.client.force_login(self.other_user)
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 403)
        
        # Author delete POST
        self.client.force_login(self.user)
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 302)
        with self.assertRaises(Report.DoesNotExist):
            self.critical_assigned.refresh_from_db()

    def test_bookmark_toggle(self):
        self.client.force_login(self.user)
        url = reverse('reports:toggle_bookmark', kwargs={'report_uuid': self.normal_report.uuid})
        
        # Initial POST bookmarks it
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Bookmarked")
        
        # Second POST removes bookmark
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Bookmark")

    def test_watch_toggle(self):
        self.client.force_login(self.user)
        url = reverse('reports:toggle_watch', kwargs={'report_uuid': self.normal_report.uuid})
        
        # Initial POST watches it
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Watching")
        
        # Second POST unwatches it
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Watch")

    def test_ajax_check_duplicate(self):
        self.client.force_login(self.user)
        url = reverse('reports:ajax_check_duplicate')
        
        # Try matching title
        resp = self.client.get(url, {'title': 'Normal', 'project_uuid': self.project.uuid})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Normal Report")
        
        # Non-matching title should return empty response
        resp = self.client.get(url, {'title': 'UnrelatedTitleSearch', 'project_uuid': self.project.uuid})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content.strip(), b'')

    def test_comment_notifies_followers(self):
        # Log in other_user and watch normal_report (which was reported by self.user)
        self.client.force_login(self.other_user)
        watch_url = reverse('reports:toggle_watch', kwargs={'report_uuid': self.normal_report.uuid})
        self.client.post(watch_url)
        
        # Log in self.user and add a comment
        self.client.force_login(self.user)
        comment_url = reverse('comments:add_comment', kwargs={'report_uuid': self.normal_report.uuid})
        self.client.post(comment_url, {'text': 'This is a test follower comment'})
        
        # Check notifications for other_user
        from notifications.models import Notification
        notif = Notification.objects.filter(recipient=self.other_user, notification_type='report_commented').first()
        self.assertIsNotNone(notif)
        self.assertIn("This is a test follower comment", notif.message)

    def test_bookmarks_and_watches_page(self):
        self.client.force_login(self.user)
        
        # Bookmark and watch a report
        bookmark_url = reverse('reports:toggle_bookmark', kwargs={'report_uuid': self.normal_report.uuid})
        watch_url = reverse('reports:toggle_watch', kwargs={'report_uuid': self.normal_report.uuid})
        self.client.post(bookmark_url)
        self.client.post(watch_url)
        
        # Access page
        url = reverse('reports:bookmarks_and_watches')
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Bookmarks & Watching")
        self.assertIn(self.normal_report, resp.context['bookmarked_reports'])
        self.assertIn(self.normal_report, resp.context['watched_reports'])

    def test_multi_attachments_validation_and_creation(self):
        self.client.force_login(self.user)
        
        # Configure project max 2 attachments, only .txt files
        self.project.max_attachments = 2
        self.project.allowed_attachment_types = ".txt"
        self.project.save()
        
        from django.core.files.uploadedfile import SimpleUploadedFile
        file1 = SimpleUploadedFile("file1.txt", b"content1", content_type="text/plain")
        file2 = SimpleUploadedFile("file2.txt", b"content2", content_type="text/plain")
        file3 = SimpleUploadedFile("file3.pdf", b"content3", content_type="application/pdf")
        
        # Scenario A: Disallowed extension (.pdf)
        url = reverse('projects:reports:new', kwargs={'project_uuid': self.project.uuid})
        data = {
            'title': 'New Issue Title',
            'description': 'Description text',
            'steps': 'Steps text',
            'frequency': 'daily',
            'impact': 'high',
            'attachments': [file3],
        }
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 200) # Returns 200 because validation fails (re-renders form with errors)
        self.assertContains(resp, "is not allowed")
        
        # Scenario B: Exceed max count limit (3 files, limit is 2)
        data['attachments'] = [file1, file2, file1] # file1 repeated is still 3 uploads
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "maximum of 2 attachments")
        
        # Scenario C: Valid uploads (2 files, type .txt)
        # Re-instantiate file inputs because they are consumed by post requests
        file1 = SimpleUploadedFile("file1.txt", b"content1", content_type="text/plain")
        file2 = SimpleUploadedFile("file2.txt", b"content2", content_type="text/plain")
        data['attachments'] = [file1, file2]
        
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 302) # Redirects to report_detail on success
        
        # Verify ReportAttachment records created
        report = Report.objects.get(title='New Issue Title')
        self.assertEqual(report.attachments.count(), 2)
        self.assertEqual(report.attachments.first().filename, "file1.txt")

    def test_delete_attachment(self):
        self.client.force_login(self.user)
        
        from django.core.files.uploadedfile import SimpleUploadedFile
        from reports.models import ReportAttachment
        file_obj = SimpleUploadedFile("delete_me.txt", b"delete content", content_type="text/plain")
        attachment = ReportAttachment.objects.create(
            report=self.normal_report,
            file=file_obj,
            filename="delete_me.txt",
            file_size=14
        )
        
        url = reverse('projects:reports:delete_attachment', kwargs={'project_uuid': self.project.uuid, 'attachment_id': attachment.id})
        
        # Stranger (other_user) cannot delete
        self.client.force_login(self.other_user)
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(ReportAttachment.objects.filter(id=attachment.id).exists())
        
        # Reporter (self.user) can delete
        self.client.force_login(self.user)
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(ReportAttachment.objects.filter(id=attachment.id).exists())

    def test_global_search_and_filters(self):
        self.client.force_login(self.user)
        
        # 1. Global Search query match
        url = reverse('global_search')
        resp = self.client.get(url, {'q': 'Normal'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Normal Report")

        # 2. Filter by status
        resp = self.client.get(url, {'status': 'resolved'})
        self.assertEqual(resp.status_code, 200)
        # Verify it does NOT contain the unresolved normal_report in the reports context list
        self.assertNotIn(self.normal_report, resp.context['reports'])

        # 3. Filter by assignee
        resp = self.client.get(url, {'assignee_id': self.user.id})
        self.assertEqual(resp.status_code, 200)
        self.assertIn(self.critical_assigned, resp.context['reports'])

    def test_recent_searches_session(self):
        self.client.force_login(self.user)
        url = reverse('global_search')
        
        # Search for a query
        self.client.get(url, {'q': 'testquery'})
        
        # Verify it is stored in session
        session = self.client.session
        self.assertIn('testquery', session.get('recent_searches', []))

    def test_saved_searches_crud(self):
        self.client.force_login(self.user)
        
        # 1. Save search via POST
        save_url = reverse('reports:save_search')
        resp = self.client.post(save_url, {
            'name': 'My Filtered Search',
            'q': 'bug',
            'status': 'open',
            'impact': 'high'
        })
        self.assertEqual(resp.status_code, 302) # Redirects back
        
        from reports.models import SavedSearch
        saved = SavedSearch.objects.filter(user=self.user, name='My Filtered Search').first()
        self.assertIsNotNone(saved)
        self.assertEqual(saved.query, 'bug')
        self.assertEqual(saved.filters.get('status'), 'open')
        self.assertEqual(saved.filters.get('impact'), 'high')

        # 2. Delete search via POST
        delete_url = reverse('reports:delete_saved_search', kwargs={'search_id': saved.id})
        resp = self.client.post(delete_url)
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(SavedSearch.objects.filter(id=saved.id).exists())

    def test_on_page_filtering_and_sorting(self):
        self.client.force_login(self.user)
        
        # Access report list with sorting
        list_url = reverse('projects:reports:report_list', kwargs={'project_uuid': self.project.uuid})
        
        # Sort oldest first
        resp = self.client.get(list_url, {'sort_by': 'oldest'})
        self.assertEqual(resp.status_code, 200)
        
        # Filter by status
        resp = self.client.get(list_url, {'status': 'resolved'})
        self.assertEqual(resp.status_code, 200)
        self.assertNotIn(self.normal_report, resp.context['reports'])

    def test_global_search_glimpse_view(self):
        self.client.force_login(self.user)
        url = reverse('global_search_glimpse')
        
        # 1. Empty query (Recent searches preview)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'search_glimpse_partial.html')

        # 2. Filled query (Glimpse results)
        resp = self.client.get(url, {'q': 'Normal'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Normal Report')

    def test_global_search_highlight_feature(self):
        self.client.force_login(self.user)
        url = reverse('global_search')
        
        # Request highlight for normal report
        resp = self.client.get(url, {'q': 'Normal', 'highlight': f'report:{self.normal_report.uuid}'})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['highlighted_report'], self.normal_report)
        # Verify it has been excluded from normal lists context to avoid double rendering
        self.assertNotIn(self.normal_report, resp.context['reports'])


class PrivateProjectPublicReportingTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username='owner', email='owner@example.com', password='password')
        self.reporter = User.objects.create_user(username='reporter', email='reporter@example.com', password='password')
        self.other = User.objects.create_user(username='other', email='other@example.com', password='password')
        
        # Private project
        self.project = Project.objects.create(
            title='Private Project', 
            link='https://example.com', 
            description='desc', 
            owner=self.owner,
            visibility='private',
            public=False,
            public_reporting_enabled=True
        )
        
        # Create active public link
        from public_portal.models import PublicReportingLink
        self.public_link = PublicReportingLink.objects.create(
            project=self.project,
            is_active=True,
            allow_anonymous=False
        )

    def test_cannot_report_on_private_project_without_active_public_link(self):
        # Disable public link
        self.public_link.is_active = False
        self.public_link.save()
        
        self.client.force_login(self.reporter)
        url = reverse('projects:reports:new', kwargs={'project_uuid': self.project.uuid})
        
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 403)

    def test_can_report_on_private_project_with_active_public_link(self):
        self.client.force_login(self.reporter)
        url = reverse('projects:reports:new', kwargs={'project_uuid': self.project.uuid})
        
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.context['is_public_reporter'])

    def test_can_submit_report_and_view_its_details(self):
        self.client.force_login(self.reporter)
        
        # Submit report
        url = reverse('projects:reports:new', kwargs={'project_uuid': self.project.uuid})
        resp = self.client.post(url, {
            'title': 'Test Public Report',
            'description': 'Description content',
            'steps': 'steps to reproduce',
            'frequency': 'once',
            'impact': 'medium',
            'project': self.project.id,
            'visibility': True,
        })
        self.assertEqual(resp.status_code, 302)
        
        # Retrieve report
        report = Report.objects.get(title='Test Public Report')
        self.assertEqual(report.reported_by, self.reporter)
        
        # Access report details (allowed because they are the reporter)
        detail_url = reverse('projects:reports:report_detail', kwargs={'project_uuid': self.project.uuid, 'report_uuid': report.uuid})
        resp = self.client.get(detail_url)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(resp.context['has_project_access'])

        # Other unrelated user cannot access details
        self.client.force_login(self.other)
        resp = self.client.get(detail_url)
        self.assertEqual(resp.status_code, 403)

