"""
public_portal/forms.py

Anonymous report submission form with:
- Honeypot field (must be empty)
- Server-side math CAPTCHA (no external service)
- Optional reporter contact info
- Attachment support gated by project settings
"""
from django import forms
from components.models import Component


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

    def __init__(self, *args, project=None, expected_captcha=None, allow_attachments=False, **kwargs):
        super().__init__(*args, **kwargs)
        self._expected_captcha = expected_captcha

        # Filter components to this project's components
        if project:
            self.fields['component'].queryset = Component.objects.filter(project=project)

        # Hide attachment field if project doesn't allow it for anon reports
        if not allow_attachments:
            del self.fields['attachment']

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
            max_size = 10 * 1024 * 1024  # 10 MB hard cap for anon reports
            if attachment.size > max_size:
                raise forms.ValidationError("File too large. Maximum size is 10 MB.")
        return attachment
