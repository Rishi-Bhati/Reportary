
from django import forms
from .models import User

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['name', 'username', 'github_link']

    def __init__(self, *args, **kwargs):
        super(UserProfileForm, self).__init__(*args, **kwargs)
        self.fields['name'].widget.attrs.update(
            {'class': 'input input-bordered w-full', 'placeholder': 'Your full name'})
        self.fields['username'].widget.attrs.update(
            {'class': 'input input-bordered w-full', 'placeholder': 'A unique username'})
        self.fields['github_link'].widget.attrs.update(
            {'class': 'input input-bordered w-full', 'placeholder': 'https://github.com/your-username'})
