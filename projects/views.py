from django.shortcuts import render, redirect
from .forms import ProjectForm, ComponentFormSet, ComponentForm, ComponentFormSet
from django.contrib.auth.decorators import login_required
from projects.models import Project
from django.http import HttpResponseForbidden
from accounts.models import User

# Create your views here.


@login_required
def register_project(request):
    if request.method == "POST":
        project_form = ProjectForm(request.POST)        
        
        if project_form.is_valid():
            # Save the project
            project = project_form.save(commit=False)
            project.owner = request.user
            project.save()
            project.collaborators.add(request.user)

            collaborators_emails = request.POST.get('collaborators', '')
            if collaborators_emails:
                emails = [email.strip() for email in collaborators_emails.split(',')]
                for email in emails:
                    user = User.objects.filter(email=email).first()
                    if user:
                        project.collaborators.add(user)

            component_formset = ComponentFormSet(request.POST, instance=project, prefix='components')
            if component_formset.is_valid():
                component_formset.save()
                return redirect("projects:projects_view")
    else:
        project_form = ProjectForm()
        component_formset = ComponentFormSet(instance=Project(), prefix='components')
    
    return render(request, 'register_project.html', {
        'form': project_form,
        'component_formset': component_formset,
    })



def projects_view(request):
    projects = Project.objects.filter(public=True)
    return render(request, 'projects_view.html', {'projects': projects})



def project_detail(request, pk):
    user = request.user

    # if user is the owner of the project, show all the details and give option to edit, else show only public details and no edit option
    project = Project.objects.get(pk=pk)
    is_owner = user.is_authenticated and (project.owner == user)    
    return render(request, 'project_details.html', {
        'project': project,
        'is_owner': is_owner,
    })


@login_required
def edit_project(request, pk):
    project = Project.objects.get(pk=pk)
    
    if project.owner != request.user:
        return HttpResponseForbidden("You are not the owner of this project.")

    if request.method == "POST":
        project_form = ProjectForm(request.POST, instance=project)
        component_formset = ComponentFormSet(request.POST, instance=project, prefix='components')
        
        if project_form.is_valid() and component_formset.is_valid():
            project = project_form.save()
            component_formset.save()

            project.collaborators.clear()
            project.collaborators.add(request.user)
            collaborators_emails = request.POST.get('collaborators', '')
            if collaborators_emails:
                emails = [email.strip() for email in collaborators_emails.split(',')]
                for email in emails:
                    user = User.objects.filter(email=email).first()
                    if user:
                        project.collaborators.add(user)

            return redirect("projects:project_detail", pk=project.pk)
    else:
        project_form = ProjectForm(instance=project)
        component_formset = ComponentFormSet(instance=project, prefix='components')
    
    collaborator_email_list = [user.email for user in project.collaborators.all()]
    return render(request, 'edit_project.html', {
        'form': project_form,
        'component_formset': component_formset,
        'project': project,
        'collaborator_email_list': collaborator_email_list,
        'collaborator_emails': ", ".join(collaborator_email_list)
    })


@login_required
def my_projects_view(request):
    projects = Project.objects.filter(owner=request.user)
    return render(request, 'projects_view.html', {'projects': projects})
