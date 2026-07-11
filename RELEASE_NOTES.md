# Release Notes - v1.0.0-beta.1 (Major Public Beta)

**Date**: July 12, 2026

## Overview
This is the first versioned release of Reportary — **v1.0.0-beta.1**. It consolidates everything shipped between Phase 2.0 and now into a single cohesive release, covering a major security audit, new features, UX polish, administration tools, and all the pages needed for a public launch.

## Security Fixes

### 🔴 Endpoint Security Hardening
Multiple endpoints were accessible without authentication and have been remediated:
- `GET /reports/get_components/` — now requires login + project membership check
- `GET /reports/get_project_config/` — now requires login + project membership check
- `GET /search/` and `GET /search/glimpse/` — now require login
- `GET /profile/` — now requires login
- `my_report_list` and `assigned_to_me` views — replaced weak manual auth checks with `@login_required`

### 🔴 Global HTMX CSRF Token Fix
HTMX-driven POST/PUT/DELETE requests (task toggles, bookmarks, comment actions, reactions) were silently rejected due to missing CSRF token headers. Fixed via a centralised `htmx:configRequest` event handler in `base.html` that automatically injects the CSRF token for all HTMX mutations site-wide.

## New Features

### Project Dashboard
Every project now has a dedicated dashboard showing:
- Real-time statistics (open/resolved/total reports, critical count)
- Dynamic project health score (0–100)
- Recent reports with status indicators
- Active collaborators with avatars
- Interactive task checklist — fully persistent, toggle/add/delete without page reloads

### Global Search — Real-time Popdown
- Live result popdown as you type (no Enter required) via HTMX
- Results span projects, reports, comments, and organisations
- Recent searches shown on focus; saved in session
- Clicking a result navigates directly and highlights the selected item on the full search results page
- Contextual filters on the full results page: status, severity, assignee, date range

### Filter & Sort on Every List View
All list views (reports, projects, organisations) now have contextual filter and sort controls:
- Reports: status, severity, assignee, date range
- Projects: visibility (public/private), creation date

### Bookmark & Watch Reports
- Bookmark any report for quick access from a dedicated Bookmarks & Watches view
- Watch a report to receive in-app notifications on status, assignee, or severity changes

## UX Improvements

### Toast Notifications
Replaced inline Django messages with an animated toast notification system. Toasts slide in from the top-right with a countdown progress bar and auto-dismiss after 4 seconds. All success, error, warning, and info messages now display as toasts.

### HTMX Global Loading Bar
A thin blue progress bar appears at the very top of every page during any HTMX request, providing clear visual feedback on network activity.

### Notification Centre Redesign
- Cleaner layout and improved empty state
- Invite cards have inline accept/decline buttons
- Unread badge count now reflects accurate server-side counts

## Administration

### Site Announcements (Superuser Only)
Superusers can now post site-wide announcement banners from the Django admin. Banners support four levels — Info, Warning, Critical, Success — are dismissable by users, and support optional auto-expiry via a date/time field.

### Account Deletion (Soft-delete with 30-day Hard-delete)
Users can delete their account from the Edit Profile > Danger Zone section. Requires password confirmation. On deletion:
1. Account is immediately deactivated (`is_active=False`)
2. `scheduled_deletion_date` is set to 30 days from now
3. User is logged out and redirected to the landing page
4. Account is permanently and irreversibly deleted after 30 days by the `purge_deleted_accounts` management command
5. User can reactivate at any time within the 30-day window by simply logging back in

### Improved Django Admin
- All models now registered with `list_display`, filters, search, and ordering
- `UserAdmin` includes `is_active`, `type`, `is_email_verified`, `scheduled_deletion_date`, and a `reactivate_accounts` bulk action
- `AuditLogAdmin` is read-only (immutable audit trail)
- `AnnouncementAdmin` restricted to superusers only

## Launch Readiness

- **FAQ page** (`/faq/`) — 10-question accordion FAQ
- **Privacy Policy** (`/privacy/`) — full policy covering data collection, storage, retention, and deletion
- **Terms of Service** (`/terms/`) — comprehensive terms
- **Contact page** (`/contact/`) — form submissions routed to `anujkumar123.mp@gmail.com`
- **Landing page** — upgraded footer with Product / Support / Legal link columns; badge updated to `v1.0.0-beta.1`
- **Sidebar** — new Help section with FAQ and Contact links

## Technical

- Migration `accounts.0011_user_scheduled_deletion_date` — adds `scheduled_deletion_date` to the User model
- Migration `core.0001_initial` — creates the `Announcement` model
- New management command: `python manage.py purge_deleted_accounts [--dry-run]`
- `core` app added to `INSTALLED_APPS` for model and admin registration
- `core.context_processors.announcements` added to template context processors
- `CONTACT_EMAIL = 'anujkumar123.mp@gmail.com'` added to settings
- All 47 automated integration tests verified green and passing

---

# Release Notes - Phase 2.0 (Public Beta)

**Date**: July 4, 2026

## Overview
This release marks **Phase 2.0 (Public Beta)** of Reportary. It introduces crucial improvements to organizational alignment, granular access scoping, secure data identification via UUIDs, full audit logging for reports, and essential security patches.

## Key Features Shipped
*   **Basic Organization Support**:
    *   Create organizations and manage member invites.
    *   Support for organization-owned projects.
    *   Dedicated **Project Head** role with administrative access to org projects, while the organization owner remains the main head.
*   **3-Level Access Scoping**:
    *   Enforced permissions for **Public**, **Org-Only**, and **Private** visibility levels across projects, reports, and comments.
*   **Report History & Audit Logs**:
    *   Full event logging for all project modifications, issue updates (status changes, reassignments, severity updates), and collaborator actions.
*   **Basic Security Hardening**:
    *   Enforced strong password validations (minimum length, uppercase, numbers, special characters).
    *   Improved login and signup form validation with error messages displayed directly inside the authentication card.
    *   Replaced Django auto-incrementing integer PK IDs with secure, non-enumerable **UUIDv7** primary keys for all database models.
*   **Navigation & Miscellaneous UX**:
    *   Activated **Collaborating Projects** filter page.
    *   Activated **Needs Attention** view highlighting critical reports assigned to the user or reported on their projects.
    *   Integrated **What's New** changelog connected to the topbar notification bell.
    *   Unified the search box and refresh buttons in a sleek input widget.

## Technical Improvements
*   Database schema migrations applied for UUID conversion and model relationships.
*   Cleaned up leftover print and log statements.
*   All 15 automated integration tests verified green and passing.

---

# Release Notes - Phase 1.5 (Public Alpha)

**Date**: January 7, 2026

## Overview
This release marks **Phase 1.5** of Reportary. It serves as an early beta build focused on verifying core functionality, hardening access controls, and establishing the foundational workflows for project and issue management.

**Disclaimer**: This is a development build. The product is not yet feature-complete and may contain security vulnerabilities. Use with caution.

## Key Features Shipped
*   **Core Project Management**:
    *   Create and manage Projects (Public/Private).
*   **Issue Tracking Engine**:
    *   "Report New Issue" workflow with Markdown support.
    *   Fields for Severity, Impact, Reproducibility, and Attachments.
    *   Status Lifecycle (Open, In Progress, Resolved, Closed).
*   **Collaboration**:
    *   Basic comments system.
*   **Dashboard & Navigation**:
    *   Personalized dashboard with "Assigned to Me" and "Reported by Me" filters.
    *   Global Search functionality.
*   **Access Control**:
    *   Basic visibility enforcement (Private projects/reports are restricted).
    *   Collaborator management permissions.

## Security & Known Issues
*   **Security**: There are known vulnerabilities in this release. I am actively working on patching these in the upcoming Phase 2 updates.
*   **Reporting Bugs**: If you find a security flaw or a bug, please use the "Report Issue" feature within the app itself to document it.

## Technical Improvements
*   Updated UI to "Clean Blue" theme (Vintage Grape / Sapphire Sky palette).
*   Refactored `dashboard` and `project` views for better performance.
*   Fixed broken links and navigation stand-ins.

## What's Next?
*   Proper history logging for reports.
*   Organization/Team hierarchy.
*   Anonymous reporting flows.
*   Enhanced RBAC (Role-Based Access Control).
*   Third-party integrations.
