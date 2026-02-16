from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Organisation

@login_required
@require_POST
def leave_organisation(request, uuid):
    org = get_object_or_404(Organisation, uuid=uuid)
    
    if request.user in org.members.all():
        org.members.remove(request.user)
        messages.success(request, f"You have left {org.name}.")
    else:
        messages.error(request, "You are not a member of this organisation.")
        
    return redirect('profile')

