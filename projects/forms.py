from django import forms
from django.forms import inlineformset_factory
from .models import Project, Component

class ProjectForm(forms.ModelForm):
    title = forms.CharField(widget=forms.TextInput(attrs={'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}))
    link = forms.URLField(widget=forms.URLInput(attrs={'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}))
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': 4, 'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}))
    public = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-blue-600'}))

    class Meta:
        model = Project
        fields = ['title', 'link', 'description', 'public']

class ComponentForm(forms.ModelForm):
    name = forms.CharField(widget=forms.TextInput(attrs={'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}))
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': 2, 'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}))

    class Meta:
        model = Component
        fields = ['name', 'description']

ComponentFormSet = inlineformset_factory(
    Project, 
    Component, 
    form=ComponentForm, 
    extra=1, 
    can_delete=True,
    widgets={
        'DELETE': forms.CheckboxInput(attrs={'class': 'form-checkbox h-5 w-5 text-red-600'})
    }
)