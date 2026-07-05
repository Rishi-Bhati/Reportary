from django import forms
from django.forms import inlineformset_factory
from .models import Project, Component

class ProjectForm(forms.ModelForm):
    title = forms.CharField(widget=forms.TextInput(attrs={'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}))
    link = forms.URLField(widget=forms.URLInput(attrs={'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}))
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': 4, 'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}))
    visibility = forms.ChoiceField(
        choices=Project.VISIBILITY_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'radio radio-primary'}),
        initial='public',
        label="Visibility Scope"
    )

    class Meta:
        model = Project
        fields = ['title', 'link', 'description', 'org', 'project_head', 'visibility']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        self.user = user
        super().__init__(*args, **kwargs)
        
        if user:
            from organisations.services import get_user_owned_organisations
            owned_orgs = get_user_owned_organisations(user)
            self.fields['org'].queryset = owned_orgs
            
            # Project Head choices:
            # 1. The user themselves
            # 2. Any member of the user's owned organizations
            # 3. If editing, the current project_head or owner
            from accounts.models import User
            from django.db.models import Q
            
            q_filter = Q(id=user.id) | Q(organisation_members__in=owned_orgs)
            if self.instance and self.instance.pk:
                if self.instance.project_head_id:
                    q_filter |= Q(id=self.instance.project_head_id)
                q_filter |= Q(id=self.instance.owner_id)
                if self.instance.org:
                    q_filter |= Q(organisation_members=self.instance.org)
            
            self.fields['project_head'].queryset = User.objects.filter(q_filter).distinct()
            self.fields['project_head'].initial = user
        else:
            from organisations.models import Organisation
            from accounts.models import User
            self.fields['org'].queryset = Organisation.objects.none()
            self.fields['project_head'].queryset = User.objects.none()

        # Style dropdowns
        self.fields['org'].widget.attrs.update({
            'class': 'shadow border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'
        })
        self.fields['org'].required = False
        self.fields['org'].empty_label = "None (Personal Project)"

        self.fields['project_head'].widget.attrs.update({
            'class': 'shadow border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'
        })
        self.fields['project_head'].required = False
        self.fields['project_head'].label = "Project Head"

    def clean(self):
        cleaned_data = super().clean()
        org = cleaned_data.get('org')
        project_head = cleaned_data.get('project_head')
        visibility = cleaned_data.get('visibility')

        if visibility == 'org' and not org:
            self.add_error('visibility', "You must select an organization to use the 'Organization Members Only' visibility scope.")

        if org:
            if not project_head:
                # Only raise 'required' error if no project_head was submitted at all
                if not self.data.get('project_head'):
                    self.add_error('project_head', "Project Head is required for organization projects.")
            else:
                from rules.views import is_organisation_member
                if not is_organisation_member(project_head, org):
                    self.add_error('project_head', f"The project head must be a member of the selected organization '{org.name}'.")
        else:
            # Personal project: project_head is None
            cleaned_data['project_head'] = None
            if visibility == 'org':
                self.add_error('visibility', "Organization visibility is only available for organization-owned projects.")
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Update public field to sync with visibility CharField
        instance.public = (instance.visibility == 'public')
        
        # Scoping owner: Org owner for org projects, creator for personal projects
        if instance.org:
            instance.owner = instance.org.owner
        elif self.user:
            instance.owner = self.user

        # Handle project_head invite-based workflow
        if self.instance and self.instance.pk:
            try:
                old_instance = Project.objects.get(pk=self.instance.pk)
                old_head = old_instance.project_head
            except Project.DoesNotExist:
                old_head = None
            new_head = instance.project_head
            if new_head != old_head:
                # Revert to old head so it's not changed directly until accepted
                instance.project_head = old_head
                if new_head:
                    from notifications.services import create_invitation
                    # We will trigger the invite after saving to ensure db consistency
                    self.pending_project_head_invite = new_head
        else:
            new_head = instance.project_head
            if new_head:
                instance.project_head = None
                self.pending_project_head_invite = new_head

        if commit:
            instance.save()
            self._save_project_head_invite(instance)
        return instance

    def _save_project_head_invite(self, instance):
        if hasattr(self, 'pending_project_head_invite') and self.pending_project_head_invite:
            from notifications.services import create_invitation
            create_invitation(
                invite_type='project_head',
                invited_by=self.user,
                invited_user=self.pending_project_head_invite,
                project=instance
            )

class ComponentForm(forms.ModelForm):
    name = forms.CharField(widget=forms.TextInput(attrs={'class': 'input input-sm input-bordered w-full focus:border-[#226ce0]', 'placeholder': 'Name'}))
    description = forms.CharField(widget=forms.Textarea(attrs={'rows': 2, 'class': 'textarea textarea-sm textarea-bordered w-full focus:border-[#226ce0]', 'placeholder': 'Description'}))

    class Meta:
        model = Component
        fields = ['name', 'description']
        exclude = ['project', 'id']

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