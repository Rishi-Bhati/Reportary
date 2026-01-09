# Reportary

## Issue Tracking, Simplified.

Reportary is a streamlined issue tracking and project management tool designed for engineering teams. It focuses on unified data, real-time collaboration, and workflows that minimize friction.

### Phase 1.5: Functional Prototype (Public Alpha)

**Reportary is currently in Phase 1.5.** This is an early-stage functional prototype intended for **testing and feedback**. It is not a complete product. Features are evolving rapidly.

> **Security Notice:** As a prototype, this build may contain security flaws. I am aware of common vulnerabilities and will be patching them in upcoming updates. If you spot a bug or security issue, please report it directly using the "Report Issue" feature on the live site.

---

## Live Preview

**Try Reportary without installing anything.**

The best way to experience Reportary is through the live web preview.

[**Launch Reportary Live Preview**](https://reportary.onrender.com) 

---

## Key Features

*   **Project Management**: Create and manage public or private projects.
*   **Issue Reporting**: Rich reporting interface with Markdown, severity levels, and attachments.
*   **Collaboration**: Threaded comments and history logs for every issue.
*   **Dashboard**: Centralized view of your assigned tasks and reported issues.
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

*   Proper history logging for reports.
*   Organization/Team Support
*   Anonymous Reporting Workflows
*   Role-Based Access Control (RBAC)
*   Third-party Integrations

## License

Reportary is open-source software licensed under the [GNU Affero General Public License v3.0 (AGPL v3)](LICENSE.md).
