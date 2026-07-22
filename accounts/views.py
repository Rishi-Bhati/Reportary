
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import JsonResponse
from .forms import UserProfileForm
from organisations.models import Organisation

User = get_user_model()

@login_required
def user_search(request):
    # H-07: Enforce minimum query length and scope to relevant users only
    term = request.GET.get('term', '').strip()
    if len(term) < 2:
        return JsonResponse({'results': []})

    from organisations.services import get_user_organisations
    from django.db.models import Q
    user_orgs = get_user_organisations(request.user)

    # Scope: users in the same org, or existing project collaborators
    # This prevents scraping the entire user database
    users = User.objects.filter(
        Q(organisation_members__in=user_orgs) | Q(organisations__in=user_orgs)
    ).filter(
        Q(email__icontains=term) | Q(username__icontains=term)
    ).exclude(id=request.user.id).distinct()[:10]

    results = []
    for user in users:
        results.append({
            'id': user.email,
            'text': user.email
        })
    return JsonResponse({'results': results})

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
        call_name = request.POST.get('call_name')
        tag = request.POST.get('tag')
        country = request.POST.get('country')
        bio = request.POST.get('bio')

        user = request.user

        # 2. Update User Model
        if call_name:
            user.name = call_name
        
        if tag:
            # M-03: If tag is taken, return an error instead of silently ignoring it
            if User.objects.filter(username=tag).exclude(pk=user.pk).exists():
                return render(request, "accounts/partials/user_form.html", {
                    'error': f'The tag \"@{tag}\" is already taken. Please choose a different one.',
                    'prefill': {'call_name': call_name, 'tag': tag, 'bio': bio}
                })
            else:
                user.username = tag

        # We set type to normal since this is the User flow
        user.type = 'normal'
        user.save()

        # 3. Redirect to Dashboard
        return redirect('dashboard:dashboard')

    return render(request, "accounts/partials/user_form.html")

@login_required
def onboarding_org_form(request):
    if request.method == "POST":
        # 1. Get Data
        org_name = request.POST.get('org_name')
        org_domain = request.POST.get('org_domain')
        org_description = request.POST.get('org_description')
        cp_role = request.POST.get('cp_role')
        biz_email = request.POST.get('biz_email')
        call_name = request.POST.get('call_name')
        tag = request.POST.get('tag')

        user = request.user
        
        if tag:
            if User.objects.filter(username=tag).exclude(pk=user.pk).exists():
                return render(request, "accounts/partials/org_form.html", {
                    'error': f'The tag \"@{tag}\" is already taken. Please choose a different one.',
                    'prefill': {
                        'org_name': org_name,
                        'org_domain': org_domain,
                        'org_description': org_description,
                        'cp_role': cp_role,
                        'biz_email': biz_email,
                        'call_name': call_name,
                        'tag': tag
                    }
                })
            else:
                user.username = tag

        # 2. Update User Details
        if call_name:
            user.name = call_name
        if cp_role:
            user.cp_role = cp_role
        if biz_email:
            user.business_email = biz_email
            
        # 3. Set User Type
        user.type = 'cp' # Contact Person
        user.is_cp = True
        user.save()

        # 4. Create Organisation and link to user
        if org_name:
            # If user already has an organisation id, prefer not to overwrite without check
            org = Organisation.objects.create(
                owner=user,
                name=org_name,
                domain=org_domain or None,
                description=org_description or None,
            )
            # add the owner as a member
            org.members.add(user)
            org.save()

            # link to user model (stores organisation PK)
            try:
                user.organisation = org.pk
                user.save()
            except Exception:
                # if linking fails, continue but log could be added
                pass

        return redirect('dashboard:dashboard')

    return render(request, "accounts/partials/org_form.html")


@login_required
def onboarding_dev_form(request):
    if request.method == "POST":
        # 1. Get Data
        call_name = request.POST.get('call_name')
        tag = request.POST.get('tag')
        github = request.POST.get('github')
        country = request.POST.get('country')
        bio = request.POST.get('bio')

        user = request.user

        # 2. Update User Model
        if call_name:
            user.name = call_name
        if tag:
            # M-03: If tag is taken, return an error instead of silently ignoring it
            if User.objects.filter(username=tag).exclude(pk=user.pk).exists():
                return render(request, "accounts/partials/dev_form.html", {
                    'error': f'The tag \"@{tag}\" is already taken. Please choose a different one.',
                    'prefill': {'call_name': call_name, 'tag': tag, 'bio': bio, 'github': github}
                })
            else:
                user.username = tag
        if github:
            user.github_link = github

        # We set type to dev since this is the Developer flow
        user.type = 'dev'
        user.save()

        # 3. Redirect to Dashboard
        return redirect('dashboard:dashboard')

    return render(request, "accounts/partials/dev_form.html")


@login_required
def edit_profile(request):
    user = request.user
    original_email = user.email
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            new_email = form.cleaned_data.get('email')
            
            # Create a clone of user instance to save without email first
            profile_instance = form.save(commit=False)
            
            if new_email and new_email != original_email:
                # 1. Reset email in profile_instance to original_email immediately
                profile_instance.email = original_email
                # 2. Store the new email in pending_email
                profile_instance.pending_email = new_email
                profile_instance.save()
                
                # Send email change confirmation
                import base64
                from django.contrib.auth.tokens import default_token_generator
                from django.utils.http import urlsafe_base64_encode
                from django.utils.encoding import force_bytes
                from django.urls import reverse
                from notifications.email_service import send_notification_email
                
                uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                new_email_b64 = base64.urlsafe_b64encode(new_email.encode('utf-8')).decode('utf-8')
                
                confirm_url = request.build_absolute_uri(
                    reverse('accounts:confirm_email_change', kwargs={
                        'uidb64': uidb64,
                        'token': token,
                        'new_email_b64': new_email_b64
                    })
                )
                
                context = {
                    'username': user.username,
                    'confirm_url': confirm_url,
                    'new_email': new_email,
                    'message': f"A request was made to change your Reportary email address to {new_email}. Please click the button below to confirm."
                }
                
                try:
                    send_notification_email(
                        notification_type='email_change_confirm',
                        subject="Confirm your new Reportary email address",
                        context=context,
                        to_emails=[new_email]
                    )
                    messages.info(request, f"A confirmation link has been sent to {new_email}. Please verify to complete the change.")
                except Exception as e:
                    messages.error(request, "Failed to send confirmation email. Email change is pending.")
            else:
                profile_instance.save()
                
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('home:profile')
    else:
        form = UserProfileForm(instance=user)
    
    context = {
        'form': form
    }
    return render(request, 'accounts/edit_profile.html', context)


def verify_email(request, uidb64, token):
    """View to handle token validation for signup verification."""
    from django.utils.http import urlsafe_base64_decode
    from django.utils.encoding import force_str
    from django.contrib.auth.tokens import default_token_generator
    from .email_utils import send_welcome_email

    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_email_verified = True
        user.save()
        
        # Send welcome email
        try:
            send_welcome_email(request, user)
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Failed to send welcome email: {e}")
            
        messages.success(request, "Your email has been verified successfully! Welcome to Reportary.")
    else:
        messages.error(request, "The verification link is invalid or has expired.")
        
    return redirect('home:landing_page')


@login_required
def confirm_email_change(request, uidb64, token, new_email_b64):
    """View to handle email update confirmation once link is clicked."""
    from django.utils.http import urlsafe_base64_decode
    from django.utils.encoding import force_str
    from django.contrib.auth.tokens import default_token_generator
    import base64

    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
        new_email = force_str(base64.urlsafe_b64decode(new_email_b64.encode('utf-8')))
    except (TypeError, ValueError, OverflowError, User.DoesNotExist, Exception):
        user = None
        new_email = None

    # M-13: Ensure the logged-in user is the one whose email is being changed
    if user is None or str(request.user.pk) != str(user.pk):
        messages.error(request, "You are not authorized to confirm this email change.")
        return redirect('home:profile')

    if new_email and default_token_generator.check_token(user, token):
        if User.objects.filter(email=new_email).exclude(pk=user.pk).exists():
            messages.error(request, "This email address is already in use by another account.")
        else:
            user.email = new_email
            user.pending_email = None
            user.save()
            messages.success(request, "Your email address has been updated successfully!")
    else:
        messages.error(request, "The confirmation link is invalid or has expired.")
        
    return redirect('home:profile')


@login_required
def resend_verification(request):
    """Resends email verification link to user."""
    user = request.user
    if user.is_email_verified:
        messages.info(request, "Your email is already verified.")
    else:
        from .email_utils import send_verification_email
        try:
            send_verification_email(request, user)
            messages.success(request, "Verification email has been resent to your inbox.")
        except Exception as e:
            messages.error(request, "Failed to send verification email. Please try again later.")
            
    # M-04: Validate HTTP_REFERER before using it as a redirect target
    from django.utils.http import url_has_allowed_host_and_scheme
    next_url = request.META.get('HTTP_REFERER')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect('dashboard:dashboard')


def render_verification_required(request, action_message):
    """Utility to render the verification warning page."""
    return render(request, 'accounts/email_verification_required.html', {
        'action_message': action_message
    })


@login_required
@require_POST
def delete_account(request):
    """
    Soft-deletes the user's account after password confirmation.
    Sets is_active=False and schedules permanent deletion in 30 days.
    """
    from django.contrib.auth import logout
    from django.utils import timezone
    from datetime import timedelta
    from django.utils.translation import gettext as _

    password = request.POST.get('password', '')
    user = request.user

    if not user.check_password(password):
        messages.error(request, _('Incorrect password. Account deletion cancelled.'))
        return redirect('accounts:edit_profile')

    # Soft delete: deactivate account and schedule hard-delete in 30 days
    user.is_active = False
    user.scheduled_deletion_date = timezone.now() + timedelta(days=30)
    user.save(update_fields=['is_active', 'scheduled_deletion_date'])

    logout(request)
    messages.success(request,
        _('Your account has been deactivated. It will be permanently deleted after 30 days. '
        'Log in before then to reactivate it.')
    )
    return redirect('home:landing_page')