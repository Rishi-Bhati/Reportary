"""
Tests for the portal_custom_styling beta feature.

The CSS sanitiser is the only barrier between owner-supplied CSS and a public
page, and it had no tests at all. Each bypass case below is one that the
previous regex implementation let through.
"""
from django.test import TestCase

from accounts.models import User
from beta.models import UserBetaEnrollment
from projects.models import Project
from public_portal.css_sanitizer import sanitize_and_scope_css
from public_portal.models import PortalTheme

SCOPE = '#portal-form-wrapper'


class CssSanitizerBypassTests(TestCase):
    """Each of these was a working bypass of the regex-based sanitiser."""

    def test_token_split_javascript_url_is_dropped(self):
        out = sanitize_and_scope_css('a { background: url(javasjavascript:cript:alert(1)); }')
        self.assertNotIn('javascript:', out)

    def test_token_split_expression_is_dropped(self):
        out = sanitize_and_scope_css('a { width: expresexpression(sion(alert(1)); }')
        self.assertNotIn('expression', out)

    def test_plain_expression_is_dropped(self):
        self.assertNotIn('expression', sanitize_and_scope_css('a { width: expression(alert(1)); }'))

    def test_css_escaped_external_url_is_dropped(self):
        out = sanitize_and_scope_css('a { background: url(\\68 ttps://evil.example/x.png); }')
        self.assertNotIn('evil.example', out)

    def test_plain_external_url_is_dropped(self):
        out = sanitize_and_scope_css('a { background: url(https://evil.example/x.png); }')
        self.assertNotIn('evil.example', out)

    def test_external_url_inside_a_gradient_is_dropped(self):
        out = sanitize_and_scope_css('.x { background: linear-gradient(red, url(https://evil/x)) }')
        self.assertNotIn('evil', out)

    def test_media_query_contents_are_scoped(self):
        out = sanitize_and_scope_css('@media all { body { display: none } }')
        self.assertIn('@media', out)
        self.assertIn(SCOPE, out)
        # `body` must not survive unscoped — that reached the whole page.
        self.assertNotIn('body {', out)

    def test_import_is_dropped(self):
        out = sanitize_and_scope_css('@import url(https://evil/x.css); a { color: red }')
        self.assertNotIn('@import', out)
        self.assertIn('color: red', out)

    def test_font_face_is_dropped(self):
        out = sanitize_and_scope_css('@font-face { font-family: x; src: url(https://evil/x.woff) }')
        self.assertNotIn('font-face', out)

    def test_position_is_not_an_allowed_property(self):
        out = sanitize_and_scope_css('.card { position: fixed; top: 0; color: red }')
        self.assertNotIn('position', out)
        self.assertIn('color: red', out)


class CssSanitizerBehaviourTests(TestCase):
    """The sanitiser must still be useful, and must never raise."""

    def test_ordinary_css_survives_and_is_scoped(self):
        out = sanitize_and_scope_css('.portal-card { border-radius: 4px; color: rgba(0,0,0,.5) }')
        self.assertIn(f'{SCOPE} .portal-card', out)
        self.assertIn('border-radius: 4px', out)
        self.assertIn('rgba(0,0,0,.5)', out)

    def test_relative_urls_are_allowed(self):
        out = sanitize_and_scope_css('.x { background: url(/static/img/bg.png) }')
        self.assertIn('/static/img/bg.png', out)

    def test_calc_and_var_are_allowed(self):
        out = sanitize_and_scope_css('.x { width: calc(100% - var(--portal-radius)) }')
        self.assertIn('calc(', out)
        self.assertIn('var(--portal-radius)', out)

    def test_root_selectors_collapse_onto_the_scope(self):
        out = sanitize_and_scope_css('body { background: #fff }')
        self.assertIn(f'{SCOPE} {{', out)

    def test_nested_media_does_not_swallow_following_rules(self):
        out = sanitize_and_scope_css('@media (max-width:600px){ .a{color:red} } .b{color:blue}')
        self.assertIn('color: blue', out, 'the rule after a @media block must survive')

    def test_malformed_css_never_raises(self):
        for css in ('.a { color: red', 'not css at all {{{', '}{}{', '', None):
            self.assertIsInstance(sanitize_and_scope_css(css), str)

    def test_oversized_css_is_truncated_not_rejected(self):
        huge = '.x { color: red } ' * 5000
        self.assertIsInstance(sanitize_and_scope_css(huge), str)


class PortalThemeFormTests(TestCase):
    """SEC-05 / SEC-06 — theme fields land in a <style> block and an <img src>."""

    def _form(self, **overrides):
        from public_portal.forms import PortalThemeForm

        data = {
            'primary_color': '#226ce0',
            'background_color': '#ffffff',
            'card_background': '#ffffff',
            'text_color': '#111827',
            'accent_color': '#818cf8',
            'font_family': 'Inter',
            'border_radius': '12px',
            'custom_css': '',
            'custom_logo_url': '',
            'custom_heading': '',
        }
        data.update(overrides)
        return PortalThemeForm(data)

    def test_valid_theme_is_accepted(self):
        self.assertTrue(self._form().is_valid())

    def test_css_injection_through_a_colour_field_is_rejected(self):
        form = self._form(primary_color='red; } html { display: none } .x {')
        self.assertFalse(form.is_valid())
        self.assertIn('primary_color', form.errors)

    def test_every_colour_field_is_validated(self):
        from public_portal.forms import PortalThemeForm

        for field in PortalThemeForm.COLOR_FIELDS:
            with self.subTest(field=field):
                form = self._form(**{field: 'javascript:alert(1)'})
                self.assertFalse(form.is_valid())
                self.assertIn(field, form.errors)

    def test_font_family_is_restricted_to_the_offered_choices(self):
        form = self._form(font_family='Inter&text=</style><script>')
        self.assertFalse(form.is_valid())
        self.assertIn('font_family', form.errors)

    def test_border_radius_is_restricted_to_the_offered_choices(self):
        self.assertFalse(self._form(border_radius='0; } body { display:none } .x{').is_valid())

    def test_logo_url_must_be_https(self):
        self.assertFalse(self._form(custom_logo_url='http://insecure.example/logo.png').is_valid())
        self.assertFalse(self._form(custom_logo_url='javascript:alert(1)').is_valid())
        self.assertTrue(self._form(custom_logo_url='https://cdn.example/logo.png').is_valid())

    def test_custom_css_is_length_capped(self):
        from public_portal.css_sanitizer import MAX_CSS_LENGTH

        form = self._form(custom_css='a{color:red}' * MAX_CSS_LENGTH)
        self.assertFalse(form.is_valid())
        self.assertIn('custom_css', form.errors)


class PortalThemeViewTests(TestCase):
    """BETA-10 — opening the editor must not change the live portal."""

    def setUp(self):
        self.owner = User.objects.create_user(
            email='themeowner@example.com', username='themeowner', password='Str0ngPassw!23')
        self.owner.is_email_verified = True
        self.owner.save()
        UserBetaEnrollment.objects.create(user=self.owner)
        self.project = Project.objects.create(
            owner=self.owner, title='Themed', link='http://x.com', description='d')
        self.client.force_login(self.owner)
        self.url = f'/p/project/{self.project.uuid}/theme/'

    def test_get_does_not_create_a_theme_row(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            PortalTheme.objects.filter(project=self.project).exists(),
            "merely opening the editor must not restyle the live portal",
        )

    def test_post_creates_the_theme(self):
        response = self.client.post(self.url, {
            'primary_color': '#123456', 'background_color': '#ffffff',
            'card_background': '#ffffff', 'text_color': '#111827',
            'accent_color': '#818cf8', 'font_family': 'Roboto',
            'border_radius': '4px', 'custom_css': '', 'custom_logo_url': '',
            'custom_heading': 'Report a bug',
        })
        self.assertEqual(response.status_code, 302)
        theme = PortalTheme.objects.get(project=self.project)
        self.assertEqual(theme.primary_color, '#123456')
        self.assertEqual(theme.custom_heading, 'Report a bug')

    def test_invalid_post_does_not_save(self):
        response = self.client.post(self.url, {
            'primary_color': 'red; } body { display:none } .x{',
            'background_color': '#ffffff', 'card_background': '#ffffff',
            'text_color': '#111827', 'accent_color': '#818cf8',
            'font_family': 'Inter', 'border_radius': '12px',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(PortalTheme.objects.filter(project=self.project).exists())

    def test_non_manager_is_forbidden(self):
        stranger = User.objects.create_user(
            email='stranger@example.com', username='themestranger', password='Str0ngPassw!23')
        self.client.force_login(stranger)
        self.assertEqual(self.client.get(self.url).status_code, 403)
