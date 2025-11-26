from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages

User = get_user_model()

@login_required
def onboarding_home(request):
    return render(request, "accounts/onboarding_home.html")

@login_required
def onboarding_choice(request):
    return render(request, "accounts/partials/choice.html")

@login_required
def onboarding_user_form(request):
    if request.method == "POST":
        # 1. Get Data
        call_name = request.POST.get('call_name') # "What should we call you?"
        tag = request.POST.get('tag')             # "What's your tag?"
        country = request.POST.get('country')     # Not in model yet
        bio = request.POST.get('bio')             # Not in model yet

        user = request.user

        # 2. Update User Model
        if call_name:
            user.first_name = call_name
        
        if tag:
            # Check if tag (username) is taken by someone else
            if User.objects.filter(username=tag).exclude(pk=user.pk).exists():
                # For HTMX, handling errors inline is best, but for now simple return:
                # In a real app, you'd re-render the form with an error message.
                pass 
            else:
                user.username = tag

        # We set type to normal since this is the User flow
        user.type = 'normal'
        user.save()

        # 3. Redirect to Dashboard
        return redirect('home')

    return render(request, "accounts/partials/user_form.html")

@login_required
def onboarding_org_form(request):
    if request.method == "POST":
        # 1. Get Data
        org_name = request.POST.get('org_name')
        org_domain = request.POST.get('org_domain')
        cp_role = request.POST.get('cp_role')
        biz_email = request.POST.get('biz_email')
        call_name = request.POST.get('call_name')

        user = request.user
        
        # 2. Update User Details
        if call_name:
            user.first_name = call_name
        if cp_role:
            user.cp_role = cp_role
        if biz_email:
            user.business_email = biz_email
            
        # 3. Set User Type
        user.type = 'cp' # Contact Person
        user.is_cp = True
        user.save()

        # NOTE: You haven't created an 'Organisation' model yet.
        # Ideally, you would create the Organisation object here 
        # and link it to user.organisation
        
        return redirect('home')

    return render(request, "accounts/partials/org_form.html")