"""
public_portal/views.py

Public (unauthenticated) report submission portal.
Security contract:
- Private project details are never exposed in HTML source
- All submissions are CSRF-protected
- Honeypot + math CAPTCHA filter bots
- Rate limiting caps flood attacks
- Anonymous system user absorbs reported_by FK requirement
"""
import random
import logging

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from public_portal.models import PublicReportingLink
from public_portal.forms import AnonReportForm
from public_portal.services import (
    hash_ip, check_rate_limit, get_or_create_link,
    regenerate_link, disable_link, enable_link, toggle_link_anon,
    anon_reporting_allowed,
)

logger = logging.getLogger(__name__)

# ─── CAPTCHA Helpers ──────────────────────────────────────────────────────────

def _generate_captcha(request, token: str) -> tuple[str, int]:
    """
    Generate a math CAPTCHA question, store the answer in session keyed by token.
    Returns (question_text, expected_answer).
    """
    a = random.randint(2, 15)
    b = random.randint(1, 12)
    question = f"What is {a} + {b}?"
    answer = a + b
    session_key = f'captcha_{token}'
    request.session[session_key] = answer
    request.session.modified = True
    return question, answer


def _get_captcha_answer(request, token: str) -> int | None:
    """Retrieve the stored CAPTCHA answer for this token from session."""
    return request.session.get(f'captcha_{token}')


# ─── Public Portal ────────────────────────────────────────────────────────────

def portal_view(request, token: str):
    """
    Main public submission portal.
    GET  → render the form.
    POST → validate + create anonymous report.
    """
    link = get_object_or_404(PublicReportingLink, token=token)

    # Link disabled
    if not link.is_active:
        return render(request, 'public_portal/portal_disabled.html', status=200)

    project = link.project

    # 1. If user is logged in, redirect them to the normal report page (as logged-in user)
    if request.user.is_authenticated:
        from django.urls import reverse
        report_new_url = reverse('projects:reports:new', kwargs={'project_uuid': project.uuid})
        return redirect(f"{report_new_url}?from_public_link=true")

    # 2. Check if anonymous reporting is disabled (per-link, project-level, or org-level)
    allowed, reason = anon_reporting_allowed(project)
    if not link.allow_anonymous or not allowed:
        import urllib.parse
        from django.urls import reverse
        login_url_base = reverse('home:landing_page')
        report_new_url = reverse('projects:reports:new', kwargs={'project_uuid': project.uuid})
        encoded_next = urllib.parse.quote(f"{report_new_url}?from_public_link=true")
        return redirect(f"{login_url_base}?next={encoded_next}")

    # Determine what to reveal about the project
    # Private projects: show nothing identifiable
    show_project_name = project.visibility != 'private'
    project_display_name = project.title if show_project_name else None
    allow_attachments = project.anon_attachments_enabled

    if request.method == 'POST':
        return _handle_portal_post(
            request, link, project, token, allow_attachments,
            show_project_name, project_display_name
        )

    # GET: fresh form with new CAPTCHA
    captcha_question, _ = _generate_captcha(request, token)
    form = AnonReportForm(project=project, allow_attachments=allow_attachments)
    
    # Build login URL for logged-out users to log in and report
    import urllib.parse
    from django.urls import reverse
    login_url_base = reverse('home:landing_page')
    report_new_url = reverse('projects:reports:new', kwargs={'project_uuid': project.uuid})
    encoded_next = urllib.parse.quote(f"{report_new_url}?from_public_link=true")
    login_url = f"{login_url_base}?next={encoded_next}"

    # Fetch theme details if beta is enabled
    theme = None
    sanitized_css = ""
    from beta.utils import project_has_feature
    if project_has_feature(project, 'portal_custom_styling'):
        from public_portal.models import PortalTheme
        from public_portal.css_sanitizer import sanitize_and_scope_css
        theme = PortalTheme.objects.filter(project=project).first()
        if theme and theme.custom_css:
            sanitized_css = sanitize_and_scope_css(theme.custom_css)

    return render(request, 'public_portal/portal.html', {
        'form': form,
        'link': link,
        'show_project_name': show_project_name,
        'project_name': project_display_name,
        'captcha_question': captcha_question,
        'token': token,
        'login_url': login_url,
        'theme': theme,
        'sanitized_css': sanitized_css,
    })


def _handle_portal_post(request, link, project, token, allow_attachments,
                        show_project_name, project_display_name):
    """Handle the POST submission, separated for clarity."""
    expected_captcha = _get_captcha_answer(request, token)

    # Rate limit check
    ip_hash = hash_ip(request)
    allowed, retry_after = check_rate_limit(link, ip_hash)
    if not allowed:
        logger.warning("Rate limit exceeded for ip_hash=%s link=%s", ip_hash[:8], link.pk)
        if request.headers.get('HX-Request'):
            response = HttpResponse("Too many submissions. Please wait before trying again.", status=429)
            response['Retry-After'] = str(retry_after)
            return response
        return render(request, 'public_portal/portal_rate_limited.html', {
            'retry_after_minutes': (retry_after or 3600) // 60,
        }, status=429)

    form = AnonReportForm(
        request.POST,
        files=request.FILES if allow_attachments else None,
        project=project,
        expected_captcha=expected_captcha,
        allow_attachments=allow_attachments,
    )

    # Honeypot check — silent discard
    website_value = request.POST.get('website', '')
    if website_value:
        logger.warning("Honeypot triggered for link=%s", link.pk)
        # Redirect to success page as if successful — don't tell bot it was caught
        return redirect('public_portal:submitted', token=token)

    if form.is_valid():
        try:
            report = _create_anonymous_report(form, project, link, ip_hash)
            # Invalidate captcha
            request.session.pop(f'captcha_{token}', None)
            request.session.modified = True
            from django.urls import reverse
            return redirect(reverse('public_portal:submitted', kwargs={'token': token}) + f'?tracking_id={report.uuid}')
        except Exception as e:
            logger.exception("Error creating anonymous report: %s", e)
            form.add_error(None, "An unexpected error occurred. Please try again.")

    # Fetch theme details if beta is enabled
    theme = None
    sanitized_css = ""
    from beta.utils import project_has_feature
    if project_has_feature(project, 'portal_custom_styling'):
        from public_portal.models import PortalTheme
        from public_portal.css_sanitizer import sanitize_and_scope_css
        theme = PortalTheme.objects.filter(project=project).first()
        if theme and theme.custom_css:
            sanitized_css = sanitize_and_scope_css(theme.custom_css)

    # Re-generate CAPTCHA for retry
    captcha_question, _ = _generate_captcha(request, token)
    return render(request, 'public_portal/portal.html', {
        'form': form,
        'link': link,
        'show_project_name': show_project_name,
        'project_name': project_display_name,
        'captcha_question': captcha_question,
        'token': token,
        'theme': theme,
        'sanitized_css': sanitized_css,
    })


def _create_anonymous_report(form, project, link, ip_hash):
    """
    Create the Report and AnonSubmission records atomically.
    Uses the permanent anonymous system user as reported_by.
    """
    from django.db import transaction
    from accounts.models import User
    from reports.models import Report, ReportAttachment
    from public_portal.models import AnonSubmission

    cd = form.cleaned_data

    with transaction.atomic():
        # Fetch the anonymous system user created by data migration
        anon_user = User.objects.get(email='anonymous@reportary.internal')

        report = Report.objects.create(
            title=cd['title'],
            project=project,
            reported_by=anon_user,
            description=cd['description'],
            steps=cd.get('steps', ''),
            frequency=cd.get('frequency', 'once'),
            impact=cd.get('impact', 'low'),
            component=cd.get('component'),
            is_anonymous=True,
            submitted_via_link=link,
            visibility=True,
            status='open',
        )

        # Handle optional attachment
        attachment_file = cd.get('attachment')
        if attachment_file:
            ReportAttachment.objects.create(
                report=report,
                file=attachment_file,
                filename=attachment_file.name,
                file_size=attachment_file.size,
            )

        # Record submission for rate limiting
        AnonSubmission.objects.create(
            link=link,
            ip_hash=ip_hash,
            report=report,
        )

        # Notify project owner
        try:
            from notifications.services import create_notification
            create_notification(
                recipient=project.owner,
                actor=anon_user,
                notification_type='new_report',
                title="New Anonymous Report",
                message=f"An anonymous report '{report.title}' was submitted to {project.title}.",
                target_content_type='report',
                target_uuid=report.uuid,
            )
        except Exception:
            pass  # Notification failure must not block submission

    return report


def portal_submitted(request, token: str):
    """Thank-you confirmation page after successful submission."""
    # Validate the token exists (prevent direct URL access with garbage token)
    link = get_object_or_404(PublicReportingLink, token=token)
    tracking_id = request.GET.get('tracking_id')
    return render(request, 'public_portal/submitted.html', {
        'show_project_name': link.project.visibility == 'public',  # H-08: only public, not org-visibility
        'project_name': link.project.title if link.project.visibility != 'private' else None,
        'token': token,
        'tracking_id': tracking_id,
    })


# ─── Owner-only HTMX Management Endpoints ────────────────────────────────────

@login_required
@require_http_methods(["POST"])
def htmx_toggle_link(request, project_uuid):
    """Toggle public link active/inactive."""
    from projects.models import Project
    import rules.views as rules

    project = get_object_or_404(Project, uuid=project_uuid)
    if not rules.can_manage_public_links(request.user, project):
        return HttpResponse(status=403)

    link = get_or_create_link(project)
    if link.is_active:
        link = disable_link(project, request.user)
    else:
        link = enable_link(project, request.user)

    return render(request, 'projects/partials/public_link_panel.html', {
        'project': project,
        'link': link,
        'is_owner': True,
    })


@login_required
@require_http_methods(["POST"])
def htmx_regenerate_link(request, project_uuid):
    """Regenerate the public link token."""
    from projects.models import Project
    import rules.views as rules

    project = get_object_or_404(Project, uuid=project_uuid)
    if not rules.can_manage_public_links(request.user, project):
        return HttpResponse(status=403)

    link = regenerate_link(project, request.user)
    messages.success(request, "Public reporting link regenerated. The old link is now invalid.")
    return render(request, 'projects/partials/public_link_panel.html', {
        'project': project,
        'link': link,
        'is_owner': True,
    })


@login_required
@require_http_methods(["POST"])
def htmx_toggle_anon(request, project_uuid):
    """Toggle per-link anonymous submission permission."""
    from projects.models import Project
    from public_portal.services import toggle_link_anon
    import rules.views as rules

    project = get_object_or_404(Project, uuid=project_uuid)
    if not rules.can_manage_public_links(request.user, project):
        return HttpResponse(status=403)

    link = get_or_create_link(project)
    link = toggle_link_anon(link, request.user)
    return render(request, 'projects/partials/public_link_panel.html', {
        'project': project,
        'link': link,
        'is_owner': True,
    })


@login_required
@require_http_methods(["POST"])
def htmx_toggle_project_anon(request, project_uuid):
    """Toggle project-level anon_reporting_enabled."""
    from projects.models import Project
    from audit.services import log_action
    import rules.views as rules

    project = get_object_or_404(Project, uuid=project_uuid)
    if not rules.can_manage_public_links(request.user, project):
        return HttpResponse(status=403)

    old = project.anon_reporting_enabled
    project.anon_reporting_enabled = not old
    project.save(update_fields=['anon_reporting_enabled'])
    log_action(
        actor=request.user, action='update', entity_type='Project',
        entity_id=project.uuid, field_name='anon_reporting_enabled',
        old_value=old, new_value=project.anon_reporting_enabled
    )

    link = get_or_create_link(project)
    return render(request, 'projects/partials/public_link_panel.html', {
        'project': project,
        'link': link,
        'is_owner': True,
    })


@login_required
@require_http_methods(["POST"])
def htmx_toggle_anon_attachments(request, project_uuid):
    """Toggle anon_attachments_enabled on the project."""
    from projects.models import Project
    from audit.services import log_action
    import rules.views as rules

    project = get_object_or_404(Project, uuid=project_uuid)
    if not rules.can_manage_public_links(request.user, project):
        return HttpResponse(status=403)

    old = project.anon_attachments_enabled
    project.anon_attachments_enabled = not old
    project.save(update_fields=['anon_attachments_enabled'])
    log_action(
        actor=request.user, action='update', entity_type='Project',
        entity_id=project.uuid, field_name='anon_attachments_enabled',
        old_value=old, new_value=project.anon_attachments_enabled
    )

    link = get_or_create_link(project)
    return render(request, 'projects/partials/public_link_panel.html', {
        'project': project,
        'link': link,
        'is_owner': True,
    })


@login_required
def configure_portal_theme(request, project_uuid):
    """View to configure custom portal styling (colors, font, custom CSS)."""
    from beta.utils import user_has_feature
    from projects.models import Project
    from public_portal.models import PortalTheme
    import rules.views as rules
    from django.http import HttpResponseForbidden

    project = get_object_or_404(Project, uuid=project_uuid)
    if not rules.can_manage_public_links(request.user, project):
        return HttpResponseForbidden("You don't have permission to manage this project's portal settings.")

    if not user_has_feature(request.user, 'portal_custom_styling', project=project):
        messages.warning(request, "Portal Custom Styling feature requires Beta Program enrollment.")
        return redirect('projects:project_detail', project_uuid=project.uuid)

    theme, created = PortalTheme.objects.get_or_create(project=project)

    if request.method == "POST":
        theme.primary_color = request.POST.get('primary_color', '#6366f1').strip()
        theme.background_color = request.POST.get('background_color', '#0f0f1a').strip()
        theme.card_background = request.POST.get('card_background', '#1a1a2e').strip()
        theme.text_color = request.POST.get('text_color', '#e2e8f0').strip()
        theme.accent_color = request.POST.get('accent_color', '#818cf8').strip()
        theme.font_family = request.POST.get('font_family', 'Inter').strip()
        theme.border_radius = request.POST.get('border_radius', '12px').strip()
        theme.custom_css = request.POST.get('custom_css', '').strip()
        theme.custom_logo_url = request.POST.get('custom_logo_url', '').strip() or None
        theme.custom_heading = request.POST.get('custom_heading', '').strip() or None
        
        theme.save()
        messages.success(request, "Portal theme saved successfully.")
        return redirect('public_portal:configure_theme', project_uuid=project.uuid)

    return render(request, 'public_portal/configure_theme.html', {
        'project': project,
        'theme': theme,
    })
