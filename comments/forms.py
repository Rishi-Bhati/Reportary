from django import forms
from .models import Comment

# This is a ModelForm for our Comment model.
# ModelForms are a convenient way to create a form directly from a Django model.
class CommentForm(forms.ModelForm):
    class Meta:
        # We specify the model that this form is based on.
        model = Comment
        # 'fields' is a list of fields from the model to include in the form.
        # We only need the 'text' field because the other fields ('report', 'commented_by')
        # are set programmatically in the view.
        fields = ['text']
