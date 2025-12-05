from django import forms
from reports.models import Report
from components.models import Component
from projects.models import Project


class ReportForm(forms.ModelForm):
    class Meta:
        model = Report
        exclude = ['severity', 'reported_by', 'created_at', 'updated_at']
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
        project = kwargs.pop('project', None)
        super().__init__(*args, **kwargs)
        
        self.project = project  # Store project for validation in clean()
        
        if project:
            # Remove project field entirely - it will be set in the view
            if 'project' in self.fields:
                del self.fields['project']
            self.fields['component'].queryset = Component.objects.filter(project=project)
        else:
            # Project field remains visible for user selection
            if 'project' in self.fields:
                self.fields['project'].queryset = Project.objects.all()
            self.fields['component'].queryset = Component.objects.none()
        
        # Handle component filtering for POST requests
        if self.is_bound and 'project' in self.data and self.data['project']:
            try:
                self.fields['component'].queryset = Component.objects.filter(project_id=self.data['project'])
            except (ValueError, TypeError):
                self.fields['component'].queryset = Component.objects.none()
    
    def clean(self):
        cleaned_data = super().clean()
        
        # If project was passed from URL, it should be set
        if self.project is None and 'project' not in cleaned_data:
            raise forms.ValidationError("Project is required.")
        
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set project from the stored project if it exists
        if self.project:
            instance.project = self.project
        
        if commit:
            instance.save()
        
        return instance