"""
Tests for the custom_report_forms beta feature.

The configuration is assembled from a large dynamic POST body and stored as
JSON. It had no tests and no server-side validation.
"""
from django.http import QueryDict
from django.test import TestCase

from accounts.models import User
from beta.models import UserBetaEnrollment
from components.models import Component
from projects.form_config import (
    MAX_CUSTOM_FIELDS_PER_TYPE,
    MAX_REPORT_TYPES,
    build_form_config,
    normalise_slug,
)
from projects.models import ReportFormConfig, Project, resolve_report_type_slug
from reports.models import Report


def query_dict(pairs):
    """Build a QueryDict from (key, value) pairs, allowing repeated keys."""
    qd = QueryDict(mutable=True)
    for key, value in pairs:
        qd.appendlist(key, value)
    return qd


class SlugNormalisationTests(TestCase):
    def test_slugs_are_reduced_to_a_safe_alphabet(self):
        cases = {
            'Bug Report': 'bug_report',
            "a');alert(document.cookie);//": 'a_alert_document_cookie',
            '  Spaced  Out  ': 'spaced_out',
            '<script>': 'script',
            '': '',
            '---': '',
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(normalise_slug(raw), expected)

    def test_slugs_are_length_capped(self):
        self.assertLessEqual(len(normalise_slug('x' * 500)), 50)


class BuildFormConfigTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            email='cfg@example.com', username='cfgowner', password='Str0ngPassw!23')
        self.project = Project.objects.create(
            owner=self.owner, title='Cfg', link='http://x.com', description='d')

    def test_unknown_standard_fields_are_dropped(self):
        post = query_dict([
            ('report_type_slugs', 'bug'),
            ('report_type_name_bug', 'Bug'),
            ('enabled_fields_bug', 'title'),
            ('enabled_fields_bug', 'description'),
            ('enabled_fields_bug', 'is_superuser'),
            ('default_report_type', 'bug'),
        ])
        config, errors = build_form_config(post, self.project)
        self.assertNotIn('is_superuser', config['report_types']['bug']['enabled_fields'])
        self.assertTrue(any('is_superuser' in e for e in errors))

    def test_title_and_description_cannot_be_disabled(self):
        post = query_dict([
            ('report_type_slugs', 'bug'),
            ('report_type_name_bug', 'Bug'),
            ('enabled_fields_bug', 'impact'),
            ('default_report_type', 'bug'),
        ])
        config, errors = build_form_config(post, self.project)
        enabled = config['report_types']['bug']['enabled_fields']
        self.assertIn('title', enabled)
        self.assertIn('description', enabled)
        self.assertTrue(errors)

    def test_unknown_custom_field_type_falls_back_to_text(self):
        post = query_dict([
            ('report_type_slugs', 'bug'),
            ('enabled_fields_bug', 'title'),
            ('enabled_fields_bug', 'description'),
            ('cf_name_bug', 'browser'),
            ('cf_label_bug', 'Browser'),
            ('cf_type_bug', 'file_upload_rce'),
            ('cf_choices_bug', ''),
            ('default_report_type', 'bug'),
        ])
        config, errors = build_form_config(post, self.project)
        field = config['report_types']['bug']['custom_fields'][0]
        self.assertEqual(field['type'], 'text')
        self.assertTrue(any('file_upload_rce' in e for e in errors))

    def test_select_without_choices_becomes_text(self):
        post = query_dict([
            ('report_type_slugs', 'bug'),
            ('enabled_fields_bug', 'title'),
            ('enabled_fields_bug', 'description'),
            ('cf_name_bug', 'browser'),
            ('cf_label_bug', 'Browser'),
            ('cf_type_bug', 'select'),
            ('cf_choices_bug', ''),
            ('default_report_type', 'bug'),
        ])
        config, errors = build_form_config(post, self.project)
        self.assertEqual(config['report_types']['bug']['custom_fields'][0]['type'], 'text')
        self.assertTrue(any('dropdown' in e for e in errors))

    def test_report_types_are_capped(self):
        pairs = [('default_report_type', 'type_0')]
        for i in range(MAX_REPORT_TYPES + 10):
            pairs.append(('report_type_slugs', f'type_{i}'))
        config, errors = build_form_config(query_dict(pairs), self.project)
        self.assertLessEqual(len(config['report_types']), MAX_REPORT_TYPES)
        self.assertTrue(errors)

    def test_custom_fields_are_capped(self):
        pairs = [('report_type_slugs', 'bug'), ('default_report_type', 'bug'),
                 ('enabled_fields_bug', 'title'), ('enabled_fields_bug', 'description')]
        for i in range(MAX_CUSTOM_FIELDS_PER_TYPE + 10):
            pairs += [('cf_name_bug', f'field_{i}'), ('cf_label_bug', f'Field {i}'),
                      ('cf_type_bug', 'text'), ('cf_choices_bug', '')]
        config, errors = build_form_config(query_dict(pairs), self.project)
        self.assertLessEqual(
            len(config['report_types']['bug']['custom_fields']), MAX_CUSTOM_FIELDS_PER_TYPE)
        self.assertTrue(errors)

    def test_default_type_must_be_one_of_the_saved_types(self):
        post = query_dict([
            ('report_type_slugs', 'bug'),
            ('enabled_fields_bug', 'title'),
            ('enabled_fields_bug', 'description'),
            ('default_report_type', 'does_not_exist'),
        ])
        config, errors = build_form_config(post, self.project)
        self.assertEqual(config['default_report_type'], 'bug')
        self.assertTrue(errors)

    def test_injected_slug_is_normalised(self):
        post = query_dict([
            ('report_type_slugs', "x');alert(1);//"),
            ('default_report_type', 'x_alert_1'),
        ])
        config, _ = build_form_config(post, self.project)
        for slug in config['report_types']:
            self.assertRegex(slug, r'^[a-z0-9_]+$')

    def test_component_frequency_overrides_are_parsed(self):
        component = Component.objects.create(
            project=self.project, name='API', description='d')
        post = query_dict([
            ('report_type_slugs', 'bug'),
            ('enabled_fields_bug', 'title'),
            ('enabled_fields_bug', 'description'),
            ('default_report_type', 'bug'),
            (f'comp_freq_{component.uuid}', 'daily:Every day, weekly:Every week'),
        ])
        config, _ = build_form_config(post, self.project)
        overrides = config['component_frequencies'][str(component.uuid)]
        self.assertEqual(overrides[0], {'value': 'daily', 'label': 'Every day'})


class ReportTypeResolutionTests(TestCase):
    """BETA-07 — report_type is untrusted input on every submission path."""

    def setUp(self):
        self.owner = User.objects.create_user(
            email='rt@example.com', username='rtowner', password='Str0ngPassw!23')
        self.owner.is_email_verified = True
        self.owner.save()
        self.project = Project.objects.create(
            owner=self.owner, title='RT', link='http://x.com', description='d')

    def test_unknown_slug_resolves_to_the_default(self):
        self.assertEqual(resolve_report_type_slug(self.project, 'nope'), 'bug')

    def test_overlong_slug_never_reaches_the_column(self):
        resolved = resolve_report_type_slug(self.project, 'X' * 200)
        self.assertLessEqual(len(resolved), 50)

    def test_configured_slug_is_honoured(self):
        ReportFormConfig.objects.create(project=self.project, config={
            'report_types': {'vuln': {'name': 'Vulnerability',
                                      'enabled_fields': ['title', 'description'],
                                      'custom_fields': []}},
            'default_report_type': 'vuln',
        })
        self.assertEqual(resolve_report_type_slug(self.project, 'vuln'), 'vuln')

    def test_submitted_report_type_cannot_overflow_the_column(self):
        self.client.force_login(self.owner)
        response = self.client.post(f'/projects/{self.project.uuid}/reports/new/', {
            'title': 'RT probe', 'description': 'd', 'steps': 's',
            'frequency': 'once', 'impact': 'low', 'report_type': 'X' * 80,
        })
        self.assertEqual(response.status_code, 302)
        report = Report.objects.get(title='RT probe')
        self.assertLessEqual(len(report.report_type), 50)
        self.assertEqual(report.report_type, 'bug')


class HiddenTitleFieldTests(TestCase):
    """BETA-06 — hiding the title field used to brick the form after one report."""

    def setUp(self):
        self.owner = User.objects.create_user(
            email='ht@example.com', username='htowner', password='Str0ngPassw!23')
        self.owner.is_email_verified = True
        self.owner.save()
        UserBetaEnrollment.objects.create(user=self.owner)
        self.project = Project.objects.create(
            owner=self.owner, title='HT', link='http://x.com', description='d')
        # A config written before title became mandatory.
        ReportFormConfig.objects.create(project=self.project, config={
            'report_types': {'bug': {'name': 'Bug', 'enabled_fields': ['description'],
                                     'custom_fields': []}},
            'default_report_type': 'bug',
        })
        self.client.force_login(self.owner)
        self.url = f'/projects/{self.project.uuid}/reports/new/'

    def test_multiple_reports_can_be_filed(self):
        first = self.client.post(self.url, {'description': 'first', 'report_type': 'bug'})
        second = self.client.post(self.url, {'description': 'second', 'report_type': 'bug'})

        self.assertEqual(first.status_code, 302)
        self.assertEqual(second.status_code, 302, 'the second report must not be rejected')
        self.assertEqual(Report.objects.filter(project=self.project).count(), 2)

    def test_generated_titles_are_unique(self):
        self.client.post(self.url, {'description': 'a', 'report_type': 'bug'})
        self.client.post(self.url, {'description': 'b', 'report_type': 'bug'})
        titles = set(Report.objects.filter(project=self.project).values_list('title', flat=True))
        self.assertEqual(len(titles), 2)

    def test_a_rendered_but_blank_title_still_errors(self):
        """The fallback must not swallow ordinary required-field validation."""
        plain = Project.objects.create(
            owner=self.owner, title='Plain', link='http://x.com', description='d')
        response = self.client.post(f'/projects/{plain.uuid}/reports/new/', {
            'title': '', 'description': '', 'steps': '', 'frequency': 'once', 'impact': 'low',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Report.objects.filter(project=plain).exists())


class FormConfigPermissionTests(TestCase):
    """BETA-09 — the gate must match every other project-management view."""

    def setUp(self):
        self.owner = User.objects.create_user(
            email='fcp@example.com', username='fcpowner', password='Str0ngPassw!23')
        self.head = User.objects.create_user(
            email='fcphead@example.com', username='fcphead', password='Str0ngPassw!23')
        self.stranger = User.objects.create_user(
            email='fcpx@example.com', username='fcpstranger', password='Str0ngPassw!23')
        for user in (self.owner, self.head, self.stranger):
            user.is_email_verified = True
            user.save()
            UserBetaEnrollment.objects.create(user=user)

        self.project = Project.objects.create(
            owner=self.owner, title='FCP', link='http://x.com', description='d',
            project_head=self.head)
        self.url = f'/projects/{self.project.uuid}/form-config/'

    def test_project_head_can_configure(self):
        self.client.force_login(self.head)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_owner_can_configure(self):
        self.client.force_login(self.owner)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_stranger_is_forbidden(self):
        self.client.force_login(self.stranger)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_unenrolled_owner_is_redirected_not_crashed(self):
        UserBetaEnrollment.objects.filter(user=self.owner).delete()
        self.client.force_login(self.owner)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)

    def test_removing_a_type_in_use_warns_instead_of_silently_orphaning(self):
        Report.objects.create(
            title='Existing', project=self.project, reported_by=self.owner,
            description='d', steps='s', report_type='bug')
        self.client.force_login(self.owner)

        response = self.client.post(self.url, {
            'report_type_slugs': ['feature'],
            'report_type_name_feature': 'Feature',
            'enabled_fields_feature': ['title', 'description'],
            'default_report_type': 'feature',
        }, follow=True)

        messages = [str(m) for m in response.context['messages']]
        self.assertTrue(
            any("removed type 'bug'" in m for m in messages),
            f"expected a warning about orphaned reports, got: {messages}",
        )
