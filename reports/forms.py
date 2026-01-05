from django import forms
from reports.models import Report
from components.models import Component
from projects.models import Project


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        exclude = ['severity', 'reported_by', 'assigned_to', 'status', 'created_at', 'updated_at']
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
        super().__init__(*args, **kwargs)
        
        # Store the project as an instance variable so we can access it in clean() and save() methods
        # This is crucial because we need to know later if a project was pre-set from the URL
        self.project = project
        
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
            
            # Keep the project field visible and allow them to select from all projects
            if 'project' in self.fields:
                self.fields['project'].queryset = Project.objects.all()
            
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
    
    def clean(self):
        """
        Custom validation method that Django calls during form.is_valid()
        
        This ensures that a project is always provided:
        - Either via the URL parameter (stored in self.project)
        - Or via the form submission (in cleaned_data['project'])
        
        Without this, form submission from /reports/new/ without selecting a project
        would pass validation but fail when trying to save (NOT NULL constraint error)
        """
        cleaned_data = super().clean()
        
        # Check if neither route provided a project
        if self.project is None and 'project' not in cleaned_data:
            raise forms.ValidationError("Project is required.")
        
        return cleaned_data
    
    def save(self, commit=True):
        """
        Custom save method that handles setting the project field securely
        
        Why this is important:
        - If project came from URL (self.project is set), we use that value
        - We ignore whatever was submitted in the form data for the project field
        - This prevents tampering: even if someone tries to modify the form data,
          the backend uses the URL parameter instead
        """
        instance = super().save(commit=False)
        
        # If a project was passed from the URL, set it on the instance
        # This ensures the report is created for the correct project
        # regardless of what the form submission contained
        if self.project:
            instance.project = self.project
        
        if commit:
            instance.save()
        
        return instance