# Reportary

**Issue tracking, built for the way engineering teams actually work.**

Reportary is an open-source project management and issue tracking platform. It provides structured workflows for reporting, triaging, and resolving bugs and tasks — with strong access controls, real-time collaboration, and a clean, fast interface.

> **Current release: `v1.1.0-beta.1`** — Beta Program framework, Scoped REST API, Customizable Report Types & Dynamic Forms, and Public Portal Custom Styling.

**Live demo:** [reportary.onrender.com](https://reportary.onrender.com)

---

## What it does

- **Beta Program & Feature Flags** — Centralized feature gating for opt-in beta features with organization-wide and user-level enrollment controls.
- **Scoped REST API Engine** — Generate scoped API keys (`rpk_`/`rsk_`) with granular resource permissions (`reports`, `comments`, `projects` CRUD), metrics tracking, and built-in interactive API documentation.
- **Customizable Report Types & Dynamic Forms** — Define custom report categories per project (Bug, Feature, Vulnerability, or custom types), customize standard field visibility, and create dynamic custom fields (text, textarea, checkbox, select menus) with live HTMX reloading.
- **Portal Custom Styling** — Full theme customization (colors, typography, rounded corners, CSS variables) for public reporting portals with safe CSS sanitization and scoping.
- **Multilingual Support & Language Detection** — Complete English/Japanese UI support featuring location-based automatic geo-IP & device language selection, and a topbar visual globe dropdown toggle.
- **Anonymous Reporting & Public Portals** — Standalone feedback portal links (`/p/<token>/`) with honeypot fields, math CAPTCHAs, interactive drag-and-drop file uploaders, GDPR-compliant daily IP hashing, and customizable owner controls.
- **Issue Reporting & Triage** — Rich markdown-powered reports with severity levels, impact, reproducibility, duplicate checking, and auto-assignment to sole project members.
- **Project & Organization Management** — Role-based access (Owner, Project Head, Collaborator), 3-level visibility (`Public`, `Org-Only`, `Private`), project dashboards, health scores, and audit logs.
- **Notifications & Announcements** — In-app notification center with dedicated Announcements tab, persistent user dismissal tracking, and individual email dispatch.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5.2 (Python 3.14) |
| Frontend | TailwindCSS v4 + DaisyUI v5 |
| Interactivity | HTMX + Alpine.js |
| Database | PostgreSQL |
| File Storage | Cloudinary |
| Auth | Django built-in + `django-rules` |

---

## Running Locally

### Prerequisites

- Python 3.10+
- Node.js 18+ and npm
- PostgreSQL (or configure SQLite for development)

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/Rishi-Bhati/Reportary.git
cd Reportary

# 2. Create and activate a virtual environment
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Edit .env with your values

# 5. Run database migrations
python manage.py migrate

# 6. Build the CSS (run in a separate terminal)
cd theme/static_src && npm install && npm run dev

# 7. Start the development server
python manage.py runserver
```

The app will be available at `http://127.0.0.1:8000`.

### Required Environment Variables

| Variable | Description |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DATABASE_URL` | PostgreSQL connection string |
| `CLOUDINARY_URL` | Cloudinary connection string (for file uploads) |
| `EMAIL_HOST` | SMTP host for transactional email |
| `EMAIL_HOST_USER` | SMTP username |
| `EMAIL_HOST_PASSWORD` | SMTP password |
| `DEBUG` | Set to `False` in production |

---

## Project Structure

```
Reportary/
├── accounts/          # User model, auth views, profile, account deletion
├── audit/             # Immutable audit log model and admin
├── beta/              # Beta feature program registry, user/org enrollment & feature gates
├── comments/          # Threaded comments with visibility scoping
├── components/        # Shared UI components and utilities
├── core/              # Base templates, global search, context processors, announcements
├── dashboard/         # Personal dashboard (assigned, reported, watching, bookmarks)
├── home/              # Landing page, changelog, FAQ, privacy, terms, contact
├── notifications/     # In-app notification system & announcement tab
├── organisations/     # Organisation model, membership, invitations
├── projects/          # Project model, collaborators, tasks, form configuration
├── reports/           # Report model, create/edit/detail views, custom types & fields
├── restapi/           # Scoped API key management, JSON endpoints, metrics & docs
├── theme/             # TailwindCSS source (static_src/) and compiled output
└── core/settings.py   # Django settings
```

## Email Service Integration

Reportary integrates with a serverless email worker API for secure, high-performance transactional email delivery (replaces SMTP setup).
* **Worker API Repository:** [Serverless Email Service](https://github.com/Rishi-Bhati/Serverless-email-service)
* **Legacy SMTP Support:** The legacy Django SMTP-based email sending configuration and driver code remains fully intact as commented-out sections in `core/settings.py` and `notifications/email_service.py`. If you want to fall back to traditional SMTP (e.g. Gmail App Passwords, SendGrid, Amazon SES), you can uncomment those sections and define standard SMTP environment variables.

---

## Running Tests

```bash
python manage.py test
```

All 47 automated integration tests cover authentication, access scoping, project permissions, report CRUD, and attachment handling.

---

## Management Commands

```bash
# Purge accounts scheduled for hard-deletion (run as a cron job)
python manage.py purge_deleted_accounts

# Dry run — lists accounts that would be deleted without deleting them
python manage.py purge_deleted_accounts --dry-run
```

---

## Security

- All endpoints require authentication; project-scoped endpoints enforce membership checks.
- UUIDv7 primary keys prevent enumeration of users, projects, and reports.
- Strong password policy enforced at signup and on profile updates.
- HTMX mutations are CSRF-protected via a centralised `htmx:configRequest` handler in `base.html`.
- Account deletion is a soft-delete with a 30-day reactivation window before permanent removal.

If you discover a security vulnerability, please report it through the [issue tracker on the live site](https://reportary.onrender.com/projects/019f2e92-7f0d-78e9-92b3-9431a1014882/reports/new/) or contact the team directly.

---

## Changelog

See [RELEASE_NOTES.md](RELEASE_NOTES.md) for the full version history.

**Current version:** `v1.0.0 Stable` — July 2026

---

## Roadmap

Planned for future releases:

- Enhanced RBAC (role-based access control)
- Slack / Discord integrations
- AI-powered report summaries and duplicate detection
- REST API and webhook support

---

## Contributing

Contributions are welcome. Please open an issue before submitting a pull request to discuss the proposed change.

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/your-feature`
3. Commit with a clear message
4. Open a pull request against `main`

---

## License

Reportary is open-source software licensed under the [GNU Affero General Public License v3.0 (AGPL-3.0)](LICENSE.md).

Any modifications you deploy over a network must also be made available under the same license.
