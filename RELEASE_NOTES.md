# Release Notes - v1.0.0 Stable (Email Privacy, Scoped Access, & Performance Calibration)

**Date**: July 22, 2026

## Overview
This is the official stable production release (**v1.0.0**) of Reportary. It hardens email recipient privacy, scopes internal project details and collaborator listings to project members, enhances onboarding validations, and refines personal dashboard analytics and project health metrics for a production-ready launch.

## Key Features Shipped

### ✉️ Email Privacy & Layout Overhaul
- **Private Individual Dispatch**: The notification email service now extracts all unique primary and CC recipients and dispatches individual emails concurrently. This ensures that no recipient's email address is leaked in email headers (`To` or `Cc`) to other users.
- **Actionable Call-To-Action (CTA) Buttons**: All notification emails (assignments, updates, comments, and invitations) now include clear CTA buttons that link directly to the relevant issue page or the Notification Center.
- **Comment-First Email Layout**: Comments notifications now prioritize the comment body at the top of the email, followed by the issue detail card.
- **Separated Issue Reports vs. Manual Assignments**: Created a new notification template (`report_created.html`) for new issue submissions, keeping the manual assignment template (`report_assigned.html`) reserved strictly for actual ownership changes.

### 🏢 Onboarding & Account Validation
- **Onboarding Username Tags**: Standardized username/dev tag inputs and validation checks across all three onboarding flows (Developer, User, and Organization). Taken tags are properly checked, and validation errors are shown inline.
- **Reliable Verification Emails**: Adjusted signup token generation ordering to ensure registration verification links do not immediately expire on the first attempt.

### 🔒 Access Scoping & Metrics Calibration
- **Internal Details Privacy**: Hid the interactive task checklists, active project head, and collaborator list details on project pages from non-members, revealing only the project owner.
- **Scoped Personal Dashboards**: Personal overview dashboard metrics now exclude unrelated public projects on Reportary, displaying data only for user-related projects and organisations.
- **Refined Project Health Rating**: Adjusted project health calculation thresholds so that brand-new active projects with few open issues are not flagged as having "Critical" or "Warning" health.

---

# Release Notes - v1.0.0-rc (Global Multilingual Support & Mobile Email Templates)

**Date**: July 20, 2026

## Overview
This Release Candidate (**v1.0.0-rc**) introduces full multilingual support (English & Japanese) across the entire Reportary platform, alongside an overhauled, mobile-friendly notification email system.

## Key Features Shipped

### 🌐 Global Multilingual Support (English & Japanese)
- **Seamless Detection**: The server automatically detects the user's location via IP address geo-location and evaluates browser preferred languages, routing Japanese users to the Japanese UI transparently without intrusive prompts.
- **Visual Globe selector**: Added a customizable globe toggle (🌐) to the top navigation bar and public landing page for instant session-persistent language switching.
- **100% Translated Interface**: Translated the entire dashboard, analytics charts, status labels, tooltips, search results, FAQ, and legal pages.

### ✉️ Simplified Mobile-Responsive Notification Emails
- **Professional Design**: Overhauled transactional, assignment, comment, status change, and invitation templates to use clean, simple layouts.
- **Mobile Optimized**: Addressed formatting bugs that caused email notifications to render poorly on phone and mobile screens.

---

# Release Notes - v1.0.0-beta.2 (Security Hardening, Public Portals, & Organisation Upgrades)

**Date**: July 17, 2026

## Overview
This release (**v1.0.0-beta.2**) introduces major new capabilities, led by **Public Portals & Anonymous Reporting** to allow feedback submission without authentication. It also incorporates a comprehensive security hardening sweep based on a production readiness audit, introduces UX upgrades to the Organisations flow, global onboarding enhancements, and structural code cleanup.

## Key Features Shipped

### 🌐 Public Portals & Anonymous Reporting
A fully standalone reporting layout hosted at `/p/<token>/` that allows external users and visitors to submit issue reports anonymously.
- **Owner Link Management Panel**: Project owners and managers see a dedicated "Public Reporting Link" card in their project sidebar to:
  - Copy and share the URL.
  - Enable / Disable public access toggles.
  - Turn anonymous reporting or attachment uploads on/off.
  - Instantly regenerate or invalidate active link tokens.
  - View organization-level anonymous reporting policy warnings.
- **Drag-and-Drop Attachment Zone**: An interactive file upload dropzone that updates dynamically on file drop or selection.
- **Anti-Spam Protections**: Enforced server-side math CAPTCHAs, hidden honeypot fields to detect and reject bot scripts silently, and proxy-secure rate limits (hourly and daily caps per IP per link).
- **GDPR Compliance**: Salted daily IP hashing using SHA-256 to ensure raw IP addresses are never recorded or stored.
- **Thank-You Page & Tracking ID**: Upgraded the post-submission landing page with a modern UI layout, dashboard tracking status, and one-click Tracking ID clipboard copying.
- **Org-Wide Policy Overrides**: Added organization-wide anonymous reporting controls that can block public portals for all projects under the organisation.

## Security Hardening & Vulnerability Patches

### 🔴 Access Control & Scope Isolation
- **Role Separation (M-02 & H-01)**: Decoupled true project ownership from project manager/head roles. Allowed project managers to edit/delete reports.
- **UUID Detail Protection (H-02)**: Enforced strict report access checks scoping details strictly to UUID identifiers.
- **Reassign Scoping (H-04)**: Enforced validation in the `reassign_report` view so that assignees must be active project members.
- **Duplicate Check Authorization (M-06)**: Added validation checks to `ajax_check_duplicate` preventing unauthorized users from triggering checks.
- **Scoped Organisation & Project Views (H-03 & H-10)**: Restricted organisation listing filters to user's own organisations, and hid private projects inside org details from non-collaborators.
- **User Search Enumeration Protection (H-07)**: Scoped the user search autocomplete endpoint to members of the user's organisations only, preventing global email database harvesting.

### 🔴 Session & Request Hardening
- **Secure Cookie Flags & Headers (C-03 & H-11 & L-07)**: Hardened settings with session age constraints, secure cookie attributes (`HTTPONLY`, `SAMESITE='Lax'`), and HTTP headers (`nosniff`, `referrer-policy`, `X-Frame-Options`).
- **Open Redirect Protection (C-04 & M-04)**: Implemented host-matching validation on `?next` redirection parameters and `HTTP_REFERER` headers during logins, registrations, and token resends.
- **Rate-Limiting (H-06 & C-07)**: Added Cache-based rate limits (max 5 submissions/hour/IP) to the public contact form and fixed IP spoofing bypasses by reading the rightmost proxy IP from `X-Forwarded-For`.
- **Public Link Isolation (H-08)**: Hidden restricted project names from anonymous submitters on the public portal layout.

### 🔴 Input & Account Security
- **Tag Duplication Validation (M-03)**: Onboarding username/tag conflicts now prompt clean validation errors instead of silent discards.
- **Business Email Change Security (M-13)**: Hardened email alteration verification links to enforce login check and token owner validation.
- **UUID-based Member Removal (M-14)**: Migrated organisation member deletion from sequential integer IDs to UUIDs to prevent IDOR attacks.
- **Audit Log Sanitisation (M-12)**: Programmatically redacts sensitive parameters (`password`, `token`, `secret`) from being saved in plaintext in the database logs.

## New Features & UX Polish

### 🏢 Organisation Creation & Flow Upgrades
- **Sidebar & Profile Navigation**: Added a dedicated **Organisations** link to the sidebar menu drawer and profile topbar dropdown.
- **Inline Contact Details Gathering**: If a normal or developer user creates a new organisation, the platform now prompts them with the profile onboarding fields (Name, Business Email, and Corporate Role) to correctly align their profile state to a contact person before creation.
- **Automatic Owner Membership**: Owners are now automatically registered as active organization members upon creation.

### 🗺️ Global Onboarding Country List
- Expanded the country selection dropdown list from 3 options to all 195 countries worldwide via a modular shared include file.

## Code Cleanup & Technical Details
- **L-01**: Cleaned reports urls patterns to replace wildcard imports with explicit views.
- **L-04**: Swapped standard stdout `print()` debuggers with structured Python `logging` captures.

---

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
