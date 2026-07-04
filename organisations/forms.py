from django import forms
from .models import Organisation


class OrganisationForm(forms.ModelForm):
    """Form for creating and editing organisations."""
    
    name = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Organisation name'
        })
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={
            'rows': 4,
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'Describe your organisation...'
        }),
        required=False
    )
    domain = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'placeholder': 'example.com'
        }),
        required=False
    )

    class Meta:
        model = Organisation
        fields = ['name', 'description', 'domain']
