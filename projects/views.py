from django.shortcuts import render, redirect
from projects.forms import ProjectForm
from django.contrib.auth.decorators import login_required

# Create your views here.


@login_required
def register_project(request):
    form = ProjectForm()
    if request.method == "POST":
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.owner = request.user
            project.save()
            return redirect("home")
    return render(request, 'register_project.html', {'form': form})