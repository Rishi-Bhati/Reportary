# Reportary

## Issue Tracking, Simplified.

Reportary is a streamlined issue tracking and project management tool designed for engineering teams. It focuses on unified data, real-time collaboration, and workflows that minimize friction.

### Phase 2.0: Public Beta

**Reportary is currently in Phase 2.0.** This is a public beta build featuring robust access scoping, organization support, history logs, and security hardening.

> **Security Notice:** Security has been significantly hardened with strong password policies, input validation, and non-enumerable UUIDv7 identifiers. Please report any found bugs or security issues directly using the "Report Issue" feature on the live site.

---

## Live Preview

**Try Reportary without installing anything.**

The best way to experience Reportary is through the live web preview.

[**Launch Reportary Live Preview**](https://reportary.onrender.com) 

---

## Key Features

*   **Organization Support**: Create organizations, invite members, assign Project Heads, and collaborate under a unified space.
*   **3-Level Access Scoping**: Scope projects, reports, and comments to Public, Org-Only, or Private visibility.
*   **Project Management**: Create and manage public or private projects.
*   **Issue Reporting**: Rich reporting interface with Markdown, severity levels, and attachments.
*   **Report History & Audit Logs**: Detailed audit trails tracking who changed what and when on reports and projects.
*   **Collaboration**: Threaded comments with markdown support and togglable visibility.
*   **Dashboard**: Centralized view of your assigned tasks, collaborating projects, needs-attention items, and reported issues.
*   **Search**: Innovative global search to find what you need instantly.

## Technical Stack

Reportary is built on a modern, robust stack:
*   **Django 5** (Python)
*   **TailwindCSS**
*   **HTMX & AlpineJS**
*   **PostgreSQL**

---

## For Developers: Local Builds

If you are a developer looking to contribute or run the code locally, you can do so. However, for most users, the live preview is recommended.

<details>
<summary><strong>Click to view Local Installation Instructions</strong></summary>

### Prerequisites
*   Python 3.10+
*   Node.js & npm

### Setup
1.  Clone the repo: `git clone https://github.com/Rishi-Bhati/Reportary.git`
2.  Setup venv: `python -m venv venv && source venv/bin/activate`
3.  Install deps: `pip install -r requirements.txt`
4.  Install Tailwind: `python manage.py tailwind install`
5.  Migrate: `python manage.py migrate`
6.  Run:
    *   `python manage.py runserver`
    *   `python manage.py tailwind start` (in a separate terminal)

</details>

## Future Plans

*   Anonymous Reporting Workflows
*   Enhanced RBAC (Role-Based Access Control)
*   Third-party Integrations

## License

Reportary is open-source software licensed under the [GNU Affero General Public License v3.0 (AGPL v3)](LICENSE.md).
