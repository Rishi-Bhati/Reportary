# Walkthrough — Notifications, Invites, and Email Integration

Here is a summary of the accomplishments, changes made, and test validation for Phase 3 items 16 and 17.

---

## 🛠️ Changes Implemented

### 1. New `notifications` Django App
- **Constants (`constants.py`)**: Registry of notification types (`AUTO_READ_TYPES`, `ACTIONABLE_TYPES`).
- **Models (`models.py`)**: 
  - `Notification` tracks in-app messages, read/unread states, and linked objects via UUID.
  - `Invitation` tracks pending invites for collaborators, project heads, and organisation members.
- **Services (`services.py`)**: Core logic for creating notifications, sending invitations, marking read/unread, and handling invite acceptance/declines.
- **Email Service (`email_service.py`)**: Dispatch engine sending HTML/plaintext emails via Gmail SMTP to the designated recipient and CCs.
- **Context Processor (`context_processors.py`)**: Computes the unread notification count, making it available globally for the topbar badge.

### 2. Integration Hooks
- **Reports app (`reports/services.py`, `reports/views.py`)**:
  - Assignment change triggers `report_assigned` notifications.
  - Status change triggers `report_status_changed` notifications to related users (excluding actor).
  - Impact change triggers `report_impact_changed` notifications.
  - Creating a new issue report notifies the project owner and project head.
- **Projects app (`projects/services.py`, `projects/views.py`, `projects/forms.py`)**:
  - Adding new collaborators creates collaboration invitations (`collaborator`) instead of immediate additions.
  - Changing the designated Project Head is now invite-based, sending a designations invite (`project_head`). The head is set to the designated user only upon acceptance.
- **Organisations app (`organisations/services.py`)**:
  - Adding organisation members creates organization invitations (`organisation`) instead of immediate additions.
- **Comments app (`comments/views.py`)**:
  - Adding a comment on a report notifies the report's assignee, project owner, and project head.

### 3. UI Changes
- **Topbar Bell (`topbar.html`)**: Points to the notification center, displaying the dynamic unread notification badge count (hides when 0).
- **Sidebar Navigation (`sidebar.html`)**: Added a sparkle-styled **What's New** link pointing to the standalone changelog page.
- **Notification Center (`notification_center.html`)**: Full page for notifications grouped by tabs (**All**, **Unread**, **Invitations**), styled to match the Reportary theme. Unread items are highlighted with a blue border, and invites display Accept/Decline action buttons inline.

### 4. Configuration & Bugfixes
- **Settings (`settings.py`)**: Add app, context processor, and SMTP config using your existing env vars `MAIL_ID` and `MAIL_APP_PASSWORD`.
- **Needs Attention Bug (`reports/views.py`)**: Fixed to fetch reports with critical severity **OR** critical impact, and exclude resolved/closed reports.

---

## 🧪 Validation & Automated Testing

### Unit Tests
A comprehensive test suite of 6 unit tests was added in `notifications/tests.py`, verifying:
1. Direct creation of informational notifications.
2. Direct creation of invitation records.
3. Successful accept of collaborator invitations.
4. Successful decline of collaborator invitations.
5. Successful accept of organisation membership invitations.
6. Notification center view rendering and auto-marking informational notifications as read.

**Test results:**
- `notifications/tests.py`: 6 tests passed.
- Entire project: 27 tests run and passed successfully.
```
Ran 27 tests in 8.571s
OK
```

### 🐞 Bug Fix: Attachment file 404 (Local Media Serving)
- **Issue**: Clicking "View / Download" on a report attachment resulted in a `404 Page not found` because `MEDIA_URL` and `MEDIA_ROOT` were commented out in settings, and Django was not configured to serve media files locally in development. The file links defaulted to `/reports/...` which collided with reports app routes.
- **Resolution**:
  1. Enabled local media serving in `core/settings.py` by defining `MEDIA_URL = '/media/'` and `MEDIA_ROOT = BASE_DIR / 'media'`.
  2. Updated `core/urls.py` to include `static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)` when `settings.DEBUG` is `True`. This ensures attachments are correctly uploaded to `/media/reports/...` and served by Django in development.

### 🐞 Bug Fix: Report details navigation 404 from notification center
- **Issue**: Clicking "View Report" on a notification resulted in a `404 No Report matches the given query` because the link incorrectly passed `notif.target_uuid` as both `project_uuid` and `report_uuid`.
- **Resolution**:
  1. Updated `report_detail` view in `reports/views.py` to make the `project_uuid` parameter optional. If not provided, it fetches the report directly using its unique UUID.
  2. Changed the link in `notifications/templates/notifications/notification_center.html` to point to the direct `reports:report_detail` URL (passing only the `report_uuid`), eliminating the dependency on `project_uuid` inside the notification center.

### 📎 Attachment Visibility & Org Projects Count Correctness
- **Attachment Visibility**: Added an attachment rendering widget to `reports/templates/report_detail.html` right below the description card. When a report has an attachment, it displays a neat clip-icon card with file name, file size, and a "View / Download" action link.
  - *Defensive Check*: Implemented a `safe_attatchment_size` property on `Report` model (`reports/models.py`) to safely wrap fetching of the file size in a try-except. This prevents a `FileNotFoundError` page crash if the file was deleted/missing from disk.
- **Organisation Projects Count**: Corrected the mismatch between the project count on the organization dashboard and the actual list of projects. Updated `get_organisation_stats` service (`organisations/services.py`) to accept the requesting `user` and filtered the projects count to match the user's project visibility permissions (e.g. excluding private projects they do not participate in). Added passing of `request.user` into the service inside `organisation_dashboard` view (`organisations/views.py`).

### 🔐 Authentication Email Flow (Welcome, Verification, Password Reset, Email Change)
- **User Schema**: Added `is_email_verified` (Boolean) and `pending_email` (EmailField) tracking properties to the User model.
- **Read-Only Access for Unverified Users**:
  - Unverified users can log in and browse the site, but state-modifying actions are blocked.
  - Created a top dismissible warning banner inside the base layout: `📧 Verify your email to unlock reporting, commenting, project creation, and collaboration. [Resend verification]`
  - Clicking on blocked actions (e.g., project registration, report filing, accepting/declining invites) displays a customized warning card template `accounts/email_verification_required.html` with resend CTA and browser history navigation.
  - Adding a comment as an unverified user displays a beautiful, dynamic warning block inline in the comments area via HTMX.
  - Cannot invite unverified users as collaborators or organisation members.
- **Verification Flow**: 
  - Token links are securely dispatched upon registration. Verification updates `is_email_verified = True` and delivers a friendly HTML **Welcome Email**.
- **Change Email Confirmation**:
  - Modifying email inside Profile settings schedules a confirmation link to the new address. The address is updated in `User.email` only after the user clicks the confirmation link.
- **Password Reset Integration**:
  - Configured Django's built-in password reset framework to use custom styled HTML layouts matching the dashboard theme, delivering SMTP mail instructions to users.
- **Email Design**: Added rich, responsive HTML email templates for `welcome`, `verify_email`, `email_change_confirm`, and `password_reset_email` under the notifications template directory.
- **Testing**: Added 4 custom integration test cases to `accounts/tests.py`, bringing total tests to 27, all of which run and pass successfully.
- **Forgot Password URL Fix**: Corrected the "Forgot password?" link on the login card (`home/templates/home/partials/login_card.html`) to correctly point to the `accounts:password_reset` view instead of the `home:nota` (coming soon) page.
- **Password Reset URL Consistency**: Standardized password reset confirm and complete views under the `/accounts/password-reset/` namespace prefix. Corrected the `PasswordResetConfirmView` success URL redirect to match the newly configured `accounts/password-reset/complete/` path to resolve the 404 error upon password change confirmation.
- **Email Change Token Validation Fix**: Corrected a state mismatch in `edit_profile` view where the token was generated *while* the user's email was temporarily updated to the new email in memory. This caused the validation token to be hashed with the new email, resulting in validation failure (token invalid/expired) at confirmation time when compared to the old email stored in the database. Resetting the profile instance email to `original_email` prior to calling `make_token()` resolved this mismatch.

### 📊 Dashboard & Analytics Refactoring
- **Layout & Structure**: Redesigned the main dashboard view into a highly minimal, sleek, and tabbed panel layout containing two sections: **Overview** and **Analytics**.
- **Personal Dashboard (Overview Tab)**:
  - Added key metrics cards at the top (Assigned to Me, Reported, Pending Invites, and Average Resolution Time).
  - Implemented session-based report tracking inside `reports/views.py` (`report_detail` view) to record the last 5 reports visited. These are displayed dynamically in a "Recently Viewed" section on the overview tab.
  - Added a "Pending Invites" widget featuring inline action buttons to directly Accept/Decline project/org invitations.
- **Interactive Analytics (Analytics Tab)**:
  - Hooked up Chart.js loaded dynamically from a CDN to render visual charts.
  - Doughnut chart mapping *Open vs Closed* status distribution.
  - Bar chart showing *Severity distribution* (Critical, High, Medium, Low).
  - Doughnut chart breaking down reports by project *Component*.
  - Line graph plotting *Issues created over time* (last 30 days, dynamically backfilled with zeros for database neutrality).
  - Top active rankings for *Most Active Projects* and *Top Assignees*.
  - Calculation engine for *Average Resolution Time* (measuring time from creation to resolution).
- **Access Restrictions**: All calculations and metrics queries are strictly scoped to the projects the requesting user has permissions to view, preventing private project info leaks.
- **Testing**: Added 2 new tests to `dashboard/tests.py` verifying context variable correctness, session tracking, and access restrictions, bringing the total suite to 29 green tests.
- **Dashboard Aesthetics Polish**:
  - **Stat Card Tooltips**: Added small info (`i`) icon triggers on all metric cards in both the Overview and Analytics tabs. Hovering reveals brief, descriptions explaining the respective metric.
  - **Project Date Resizing**: Reduced the updated-at stamp size to `text-[9px]` and styled it as a subtle lower-case detail at the footer of project cards.
  - **Role Badge Minimization**: Resized Owner and Member badges inside the Organizations widget to `text-[8px]` with reduced padding for a sleeker, less intrusive appearance.
  - **Activity Timeline Alignment**: Replaced Tailwind padding (`pl-7`) and absolute positioning classes inside the "Your Activity" timeline list with precise inline CSS specifications. This guarantees the list items and timeline dots align exactly without overlapping/collapsing text blocks even when Tailwind utilities aren't fully re-compiled.
  - **Severity vs Impact Correction**: Corrected a layout bug where the dashboard's "Assigned to Me" list and the Analytics tab's charts queried the database field `severity` (which is excluded from the report forms and defaults to `low`). Switched both to query the `impact` field (which captures the user-submitted criticality level) and used `get_impact_display` for the badge rendering labels.
```
Ran 29 tests in 8.879s
OK
```
