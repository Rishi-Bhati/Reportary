"""
public_portal/forms.py

Anonymous report submission form with:
- Honeypot field (must be empty)
- Server-side math CAPTCHA (no external service)
- Optional reporter contact info
- Attachment support gated by project settings
"""
import re

from django import forms
from components.models import Component
from reports.services import validate_attachment
from projects.models import MAX_CUSTOM_FIELD_LENGTH, MAX_CUSTOM_TEXTAREA_LENGTH


class AnonReportForm(forms.Form):
    # ── Optional voluntary contact info ──────────────────────────────────────
    reporter_name = forms.CharField(
        max_length=80,
        required=False,
        label="Your name (optional)",
        widget=forms.TextInput(attrs={'placeholder': 'Anonymous', 'autocomplete': 'name'})
    )
    reporter_email = forms.EmailField(
        required=False,
        label="Your email (optional)",
        widget=forms.EmailInput(attrs={
            'placeholder': 'Leave blank to stay anonymous',
            'autocomplete': 'email'
        })
    )

    # ── Core report fields ────────────────────────────────────────────────────
    title = forms.CharField(
        max_length=200,
        label="Issue title",
        widget=forms.TextInput(attrs={'placeholder': 'Brief summary of the issue'})
    )
    description = forms.CharField(
        label="Description",
        widget=forms.Textarea(attrs={'rows': 5, 'placeholder': 'Describe what happened...'})
    )
    steps = forms.CharField(
        label="Steps to reproduce",
        widget=forms.Textarea(attrs={'rows': 4, 'placeholder': 'Step 1: ...\nStep 2: ...'}),
        required=False,
    )
    component = forms.ModelChoiceField(
        queryset=Component.objects.none(),
        required=False,
        empty_label="— Select component (optional) —",
        label="Component",
    )

    FREQ_CHOICES = (
        ('once', 'Once'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    )
    frequency = forms.ChoiceField(choices=FREQ_CHOICES, initial='once', label="How often does this occur?")

    IMPACT_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    )
    impact = forms.ChoiceField(choices=IMPACT_CHOICES, initial='low', label="Impact / Severity")

    # ── Optional attachment (only shown when project allows it) ───────────────
    attachment = forms.FileField(
        required=False,
        label="Attachment (optional)",
        help_text="Max 10 MB. Allowed types depend on project settings.",
    )

    # ── Anti-spam: honeypot ───────────────────────────────────────────────────
    # This field is hidden via CSS. Bots fill it; humans don't.
    website = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        label="",
    )

    # ── Anti-spam: math CAPTCHA ───────────────────────────────────────────────
    captcha_answer = forms.IntegerField(
        label="Spam check answer",
        widget=forms.NumberInput(attrs={'placeholder': 'Enter the answer'})
    )

    def __init__(self, *args, project=None, expected_captcha=None, allow_attachments=False, report_type_slug=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._expected_captcha = expected_captcha
        self.project = project
        self.report_type_slug = report_type_slug or 'bug'
        if self.is_bound and 'report_type' in self.data and self.data['report_type']:
            self.report_type_slug = self.data['report_type']

        # Filter components to this project's components
        if project:
            self.fields['component'].queryset = Component.objects.filter(project=project)

        # Hide attachment field if project doesn't allow it for anon reports
        if not allow_attachments:
            del self.fields['attachment']

        # ─── Custom Report Forms Beta Feature ───
        if project:
            from beta.utils import project_has_feature
            from projects.models import ReportFormConfig
            
            if project_has_feature(project, 'custom_report_forms'):
                form_config = ReportFormConfig.objects.filter(project=project).first()
                if form_config:
                    type_config = form_config.get_fields_for_type(self.report_type_slug)
                    enabled_fields = type_config.get('enabled_fields', ["title", "description", "steps", "component", "frequency", "impact", "visibility"])
                    custom_fields_schema = type_config.get('custom_fields', [])

                    # Add report_type choice field
                    types_config = form_config.get_report_types_config()
                    type_choices = [(slug, cfg.get('name', slug)) for slug, cfg in types_config.items()]
                    
                    self.fields['report_type'] = forms.ChoiceField(
                        choices=type_choices,
                        initial=self.report_type_slug,
                        required=False,
                        label="Report Type",
                        widget=forms.Select(attrs={
                            'class': 'select select-bordered w-full focus:border-[#226ce0] bg-gray-50 focus:bg-white transition-colors',
                            'hx-get': '/reports/ajax/get-report-type-fields/?is_public=true',
                            'hx-target': '#form-fields-container',
                            'hx-swap': 'innerHTML',
                            'hx-include': '[name="project"], [name="project_uuid"]'
                        })
                    )

                    # Remove disabled fields (keeping anti-spam / contact / attachment)
                    all_fields = list(self.fields.keys())
                    for field_name in all_fields:
                        if field_name in ['captcha_answer', 'website', 'reporter_name', 'reporter_email', 'attachment', 'report_type']:
                            continue
                        if field_name not in enabled_fields:
                            del self.fields[field_name]
                    
                    # Custom frequencies choice overrides
                    if 'frequency' in self.fields:
                        selected_component = None
                        selected_comp_id = None
                        if self.is_bound:
                            selected_comp_id = self.data.get('component')

                        if selected_comp_id:
                            try:
                                selected_component = Component.objects.get(id=selected_comp_id, project=project)
                            except Exception:
                                pass

                        choices = form_config.get_frequency_choices(component=selected_component)
                        self.fields['frequency'].choices = [(c['value'], c['label']) for c in choices]

                    # Inject dynamic custom fields
                    self.custom_field_names = []
                    for cf in custom_fields_schema:
                        # .get() throughout: a config written by an older version
                        # (or by hand) may be missing keys, and a KeyError here
                        # would 500 the whole report form.
                        raw_cf_name = cf.get('name')
                        if not raw_cf_name:
                            continue
                        cf_name = f"custom_field_{raw_cf_name}"
                        cf_label = cf.get('label') or raw_cf_name.replace('_', ' ').title()
                        cf_type = cf.get('type') or 'text'
                        cf_required = cf.get('required', False)
                        
                        if cf_type == 'text':
                            field = forms.CharField(label=cf_label, required=cf_required,
                                                    max_length=MAX_CUSTOM_FIELD_LENGTH,
                                                    widget=forms.TextInput(attrs={
                                'class': 'input input-bordered w-full focus:border-[#226ce0] bg-gray-50 focus:bg-white transition-colors'
                            }))
                        elif cf_type == 'textarea':
                            field = forms.CharField(label=cf_label, required=cf_required,
                                                    max_length=MAX_CUSTOM_TEXTAREA_LENGTH,
                                                    widget=forms.Textarea(attrs={
                                'rows': 4,
                                'class': 'textarea textarea-bordered w-full focus:border-[#226ce0] bg-gray-50 focus:bg-white transition-colors'
                            }))
                        elif cf_type == 'checkbox':
                            field = forms.BooleanField(label=cf_label, required=cf_required, widget=forms.CheckboxInput(attrs={
                                'class': 'form-checkbox h-5 w-5 text-blue-600 rounded'
                            }))
                        elif cf_type == 'select':
                            opts = [(opt.strip(), opt.strip()) for opt in cf.get('choices', '').split(',') if opt.strip()]
                            field = forms.ChoiceField(label=cf_label, required=cf_required, choices=opts, widget=forms.Select(attrs={
                                'class': 'select select-bordered w-full focus:border-[#226ce0] bg-gray-50 focus:bg-white transition-colors'
                            }))
                        else:
                            field = forms.CharField(label=cf_label, required=cf_required,
                                                    max_length=MAX_CUSTOM_FIELD_LENGTH)
                        
                        self.fields[cf_name] = field
                        self.custom_field_names.append(raw_cf_name)

    def clean_website(self):
        """Honeypot: if this field has any value, silently mark as spam."""
        value = self.cleaned_data.get('website', '')
        if value:
            # Raise a generic ValidationError that we treat as spam
            raise forms.ValidationError("Spam detected.")
        return value

    def clean_captcha_answer(self):
        answer = self.cleaned_data.get('captcha_answer')
        if self._expected_captcha is not None and answer != self._expected_captcha:
            raise forms.ValidationError("Incorrect answer. Please try again.")
        return answer

    def clean_attachment(self):
        attachment = self.cleaned_data.get('attachment')
        if attachment:
            validate_attachment(attachment, self.project)
        return attachment

    def clean(self):
        cleaned_data = super().clean()

        # Resolve the report type against the project's configured types. The
        # raw submitted value used to be stored directly whenever the custom
        # forms feature was off, which is the default for most projects.
        from projects.models import resolve_report_type_slug

        self.report_type_slug = resolve_report_type_slug(
            self.project, cleaned_data.get('report_type') or self.report_type_slug)
        cleaned_data['report_type'] = self.report_type_slug

        # Collect and validate dynamic custom fields
        custom_fields_data = {}
        if hasattr(self, 'custom_field_names'):
            for name in self.custom_field_names:
                field_key = f"custom_field_{name}"
                if field_key in cleaned_data:
                    custom_fields_data[name] = cleaned_data[field_key]
        self.cleaned_custom_fields = custom_fields_data

        # Fallbacks for db-required fields the project has hidden in its form
        # config. Only applied when the field is genuinely absent — a rendered
        # field left blank must still raise — and the generated title must be
        # unique, or only the first such report could ever be filed.
        from reports.models import generate_fallback_title

        if 'title' not in self.fields and not cleaned_data.get('title'):
            cleaned_data['title'] = generate_fallback_title(self.report_type_slug)
            self.errors.pop('title', None)

        if 'description' not in self.fields and not cleaned_data.get('description'):
            cleaned_data['description'] = (
                f"Submitted as {self.report_type_slug} report via public portal.")
            self.errors.pop('description', None)

        # NOTE: deliberately no duplicate-title check here. It was unscoped by
        # visibility, so an anonymous visitor holding a portal link could use
        # the error message to confirm the existence of internal, hidden reports
        # by title. De-duplication is a triage concern, not a submitter's.
        return cleaned_data


# ─── Portal Theme (beta: portal_custom_styling) ───────────────────────────────

HEX_COLOR = re.compile(r'^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{4}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})$')


class PortalThemeForm(forms.ModelForm):
    """
    Validates portal theme customisation.

    Every one of these values is interpolated into the portal's <style> block or
    its markup. They were previously assigned straight from request.POST and
    saved without full_clean(), so the model's own URLField validation never ran
    and the colour fields were an unvalidated CSS injection that bypassed the
    custom-CSS sanitiser entirely.
    """

    COLOR_FIELDS = (
        'primary_color', 'background_color', 'card_background',
        'text_color', 'accent_color',
    )

    class Meta:
        from public_portal.models import PortalTheme

        model = PortalTheme
        fields = (
            'primary_color', 'background_color', 'card_background', 'text_color',
            'accent_color', 'font_family', 'border_radius', 'custom_css',
            'custom_logo_url', 'custom_heading',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in self.COLOR_FIELDS:
            self.fields[name].required = False
        self.fields['custom_css'].required = False
        self.fields['custom_logo_url'].required = False
        self.fields['custom_heading'].required = False

    def _clean_color(self, name):
        value = (self.cleaned_data.get(name) or '').strip()
        if not value:
            return self.fields[name].initial or self._meta.model._meta.get_field(name).default
        if not HEX_COLOR.match(value):
            raise forms.ValidationError(
                "Enter a hex colour such as #226ce0."
            )
        return value.lower()

    def clean_primary_color(self):
        return self._clean_color('primary_color')

    def clean_background_color(self):
        return self._clean_color('background_color')

    def clean_card_background(self):
        return self._clean_color('card_background')

    def clean_text_color(self):
        return self._clean_color('text_color')

    def clean_accent_color(self):
        return self._clean_color('accent_color')

    def clean_custom_css(self):
        from public_portal.css_sanitizer import MAX_CSS_LENGTH

        css = self.cleaned_data.get('custom_css') or ''
        if len(css) > MAX_CSS_LENGTH:
            raise forms.ValidationError(
                f"Custom CSS is limited to {MAX_CSS_LENGTH:,} characters "
                f"(this is {len(css):,})."
            )
        return css

    def clean_custom_logo_url(self):
        url = (self.cleaned_data.get('custom_logo_url') or '').strip()
        if not url:
            return None
        if not url.lower().startswith('https://'):
            raise forms.ValidationError(
                "Logo URLs must start with https:// so the portal stays secure."
            )
        return url

    def clean_custom_heading(self):
        return (self.cleaned_data.get('custom_heading') or '').strip() or None
