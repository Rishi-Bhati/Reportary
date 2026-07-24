from django import forms
from reports.models import Report
from components.models import Component
from projects.models import Project
from django.utils.translation import gettext as _

class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        exclude = ['severity', 'reported_by', 'assigned_to', 'status', 'created_at', 'updated_at', 'report_type', 'custom_fields_data']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'
            }),
            'project': forms.Select(attrs={
                'class': 'shadow border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'
            }),
            'description': forms.Textarea(attrs={
                'rows': 5,
                'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'
            }),
            'steps': forms.Textarea(attrs={
                'rows': 5,
                'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'
            }),
            'frequency': forms.Select(attrs={'class': 'shadow border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
            'impact': forms.Select(attrs={'class': 'shadow border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
            'attatchment': forms.FileInput(attrs={'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}),
            'visibility': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600'}),
            'component': forms.Select(attrs={
                'class': 'shadow border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'
            }),
        }

    def __init__(self, *args, **kwargs):
        # Extract the 'project' parameter passed from the view
        # This allows us to know if the report is being created for a specific project (from URL)
        # or if the user is selecting a project themselves (from /reports/new/)
        project = kwargs.pop('project', None)
        user = kwargs.pop('user', None)
        report_type_slug = kwargs.pop('report_type_slug', 'bug')
        super().__init__(*args, **kwargs)
        
        # Store the project as an instance variable so we can access it in clean() and save() methods
        # This is crucial because we need to know later if a project was pre-set from the URL
        self.project = project

        # Set translated labels and placeholders
        self.fields['title'].label = _("Title")
        self.fields['title'].widget.attrs['placeholder'] = _("Brief summary of the issue")
        
        self.fields['description'].label = _("Description")
        self.fields['description'].widget.attrs['placeholder'] = _("Detailed explanation...")
        
        self.fields['steps'].label = _("Steps")
        self.fields['steps'].widget.attrs['placeholder'] = _("1. Go to...\n2. Click on...")
        
        self.fields['frequency'].label = _("Frequency")
        self.fields['frequency'].choices = [
            ('once', _('Once')),
            ('daily', _('Daily')),
            ('weekly', _('Weekly')),
            ('monthly', _('Monthly')),
        ]
        
        self.fields['impact'].label = _("Impact")
        self.fields['impact'].choices = [
            ('low', _('Low')),
            ('medium', _('Medium')),
            ('high', _('High')),
            ('critical', _('Critical')),
        ]
        
        self.fields['component'].label = _("Component")
        
        if 'project' in self.fields:
            self.fields['project'].label = _("Project")

        if 'visibility' in self.fields:
            self.fields['visibility'].label = _("Public Visibility")
        
        if 'is_anonymous' in self.fields:
            self.fields['is_anonymous'].widget.attrs.update({'class': 'form-checkbox h-5 w-5 text-blue-600 rounded'})

        
        if project:
            # SCENARIO 1: User accessed via /projects/<pk>/reports/new/
            # The project_pk is already in the URL, so we don't need to expose the project field
            
            # Remove the project field entirely from the form
            # Why? To prevent security vulnerability where users could inspect the HTML/DevTools
            # and change the hidden field value to submit reports for other projects
            # This ensures the project MUST come from the URL parameter, not the form submission
            if 'project' in self.fields:
                del self.fields['project']
            
            # Pre-filter components to only show components from this specific project
            # This way, the component dropdown only shows valid options for this project
            self.fields['component'].queryset = Component.objects.filter(project=project)
        else:
            # SCENARIO 2: User accessed via /reports/new/
            # No project in URL, so the user must select one from the dropdown
            
            # Keep the project field visible and allow them to select from accessible projects
            if 'project' in self.fields:
                if user:
                    from django.db.models import Q
                    from organisations.services import get_user_organisations
                    user_orgs = get_user_organisations(user)
                    
                    self.fields['project'].queryset = Project.objects.filter(
                        Q(public=True) |
                        Q(owner=user) |
                        Q(collaborators=user) |
                        Q(org__in=user_orgs)
                    ).distinct()
                else:
                    self.fields['project'].queryset = Project.objects.filter(public=True)
            
            # Don't pre-filter components because no project is selected yet
            # We'll let JavaScript dynamically load them when the user selects a project
            self.fields['component'].queryset = Component.objects.none()
        
        # Handle component filtering for POST requests (form submission)
        # When the form is submitted (POST request), the form data will have the selected project_id
        # We use this to filter the component options based on the submitted project
        if self.is_bound and 'project' in self.data and self.data['project']:
            try:
                # Filter components by the project_id from the form submission
                self.fields['component'].queryset = Component.objects.filter(project_id=self.data['project'])
            except (ValueError, TypeError):
                # If invalid data was submitted, show no components
                self.fields['component'].queryset = Component.objects.none()

        # ─── Custom Report Forms Beta Feature ───
        resolved_project = project
        if not resolved_project and self.is_bound and 'project' in self.data and self.data['project']:
            try:
                resolved_project = Project.objects.get(id=self.data['project'])
            except Exception:
                pass
        if not resolved_project and self.instance and self.instance.pk and getattr(self.instance, 'project', None):
            resolved_project = self.instance.project

        # Determine report type slug
        self.report_type_slug = report_type_slug
        if self.is_bound and 'report_type' in self.data and self.data['report_type']:
            self.report_type_slug = self.data['report_type']
        elif self.instance and self.instance.pk and self.instance.report_type:
            self.report_type_slug = self.instance.report_type

        if resolved_project:
            from beta.utils import user_has_feature
            from projects.models import ReportFormConfig
            
            if user_has_feature(user, 'custom_report_forms', project=resolved_project):
                form_config = ReportFormConfig.objects.filter(project=resolved_project).first()
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
                        label=_("Report Type"),
                        widget=forms.Select(attrs={
                            'class': 'select select-bordered w-full focus:border-[#226ce0] bg-gray-50 focus:bg-white transition-colors',
                            'hx-get': '/reports/ajax/get-report-type-fields/',
                            'hx-target': '#form-fields-container',
                            'hx-swap': 'innerHTML',
                            'hx-include': '[name="project"], [name="project_uuid"]'
                        })
                    )

                    # Remove disabled fields
                    all_fields = list(self.fields.keys())
                    for field_name in all_fields:
                        if field_name in ['project', 'attatchment', 'report_type']:
                            continue
                        if field_name not in enabled_fields:
                            del self.fields[field_name]
                    
                    # Custom frequencies choice overrides
                    if 'frequency' in self.fields:
                        selected_component = None
                        selected_comp_id = None
                        if self.is_bound:
                            selected_comp_id = self.data.get('component')
                        elif self.instance and self.instance.pk and self.instance.component:
                            selected_component = self.instance.component

                        if selected_comp_id and not selected_component:
                            try:
                                selected_component = Component.objects.get(id=selected_comp_id, project=resolved_project)
                            except Exception:
                                pass

                        choices = form_config.get_frequency_choices(component=selected_component)
                        self.fields['frequency'].choices = [(c['value'], c['label']) for c in choices]

                    # Inject dynamic custom fields
                    self.custom_field_names = []
                    for cf in custom_fields_schema:
                        cf_name = f"custom_field_{cf['name']}"
                        cf_label = cf['label']
                        cf_type = cf['type']
                        cf_required = cf.get('required', False)
                        
                        if cf_type == 'text':
                            field = forms.CharField(label=cf_label, required=cf_required, widget=forms.TextInput(attrs={
                                'class': 'input input-bordered w-full focus:border-[#226ce0] bg-gray-50 focus:bg-white transition-colors'
                            }))
                        elif cf_type == 'textarea':
                            field = forms.CharField(label=cf_label, required=cf_required, widget=forms.Textarea(attrs={
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
                            field = forms.CharField(label=cf_label, required=cf_required)
                        
                        # Populate initial value if editing
                        if self.instance and self.instance.pk and self.instance.custom_fields_data:
                            initial_val = self.instance.custom_fields_data.get(cf['name'])
                            if initial_val is not None:
                                field.initial = initial_val
                        
                        self.fields[cf_name] = field
                        self.custom_field_names.append(cf['name'])
    
    def clean(self):
        """
        Custom validation method that Django calls during form.is_valid()
        """
        cleaned_data = super().clean()
        
        # Check if neither route provided a project
        if self.project is None and 'project' not in cleaned_data:
            raise forms.ValidationError("Project is required.")

        # Collect and validate dynamic custom fields
        custom_fields_data = {}
        if hasattr(self, 'custom_field_names'):
            for name in self.custom_field_names:
                field_key = f"custom_field_{name}"
                if field_key in cleaned_data:
                    custom_fields_data[name] = cleaned_data[field_key]
        self.cleaned_custom_fields = custom_fields_data

        # Fallbacks for db-required fields if disabled
        title = cleaned_data.get('title')
        if not title:
            cleaned_data['title'] = f"[{self.report_type_slug.upper()}] Report"
            self.errors.pop('title', None)
        
        description = cleaned_data.get('description')
        if not description:
            cleaned_data['description'] = f"Submitted as {self.report_type_slug} report."
            self.errors.pop('description', None)

        title = cleaned_data.get('title')
        project = self.project or cleaned_data.get('project')
        if title and project:
            from reports.models import Report
            qs = Report.objects.filter(project=project, title__iexact=title)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("A report with this title already exists for this project.")
        
        return cleaned_data
    
    def save(self, commit=True):
        """
        Custom save method that handles setting the project field securely
        """
        instance = super().save(commit=False)
        
        # Set report type and custom fields data
        instance.report_type = self.report_type_slug
        if hasattr(self, 'cleaned_custom_fields'):
            instance.custom_fields_data = self.cleaned_custom_fields

        # If a project was passed from the URL, set it on the instance
        if self.project:
            instance.project = self.project
        
        if commit:
            instance.save()
        
        return instance