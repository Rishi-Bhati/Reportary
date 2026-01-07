# Reportary

## Issue Tracking, Simplified

Reportary is a streamlined issue tracking and project management tool designed for engineering teams. It focuses on unified data, real-time collaboration, and workflows that minimize friction.

### Development Status: Phase 1.5 (Early Beta)

**Important Notice:** Reportary is currently in **Phase 1.5** of its development lifecycle. This release is an early-stage build intended strictly for **testing and development purposes**. It is **not** a complete product and is currently under active early-stage development. Features may change, and stability is not guaranteed for production environments.

### Security Notice

Please be aware that this pre-release version may contain known security vulnerabilities. I am actively working on identifying and resolving these issues in upcoming updates.

If you encounter any security issues or bugs, please report them directly through the reporting functionality on the Reportary website itself.

---

## Key Features

*   **Project Management**: Create and manage public or private projects with custom visibility settings.
*   **Issue Reporting**: Innovative reporting interface with support for rich descriptions, steps to reproduce, severity levels, and attachments.
*   **Collaboration**: Threaded comments and history logs for transparent communication on every issue.
*   **Dashboard**: Centralized view of assigned reports, reported issues, and project activity.
*   **Search**: Integrated search functionality to quickly locate projects and reports.

## Technical Stack

Reportary is built on a robust, modern stack designed for performance and maintainability:

*   **Backend**: Django 5 (Python)
*   **Database**: SQLite (Development) / PostgreSQL (Production ready)
*   **Frontend**: Django Templates + HTMX
*   **Styling**: TailwindCSS (via `django-tailwind`)
*   **Interactivity**: AlpineJS

## Getting Started

Follow these instructions to set up the project locally for development and testing.

### Prerequisites

*   Python 3.10+
*   Node.js & npm (for TailwindCSS compilation)

### Installation

1.  **Clone the repository**
    ```bash
    git clone https://github.com/Rishi-Bhati/Reportary.git
    cd Reportary
    ```

2.  **Create and activate a virtual environment**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```

3.  **Install Python dependencies**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Install Frontend dependencies**
    Initialize and install the TailwindCSS dependencies.
    ```bash
    python manage.py tailwind install
    ```

5.  **Apply Database Migrations**
    ```bash
    python manage.py migrate
    ```

### Running the Application

To run Reportary locally, you need two terminal processes running simultaneously:

1.  **Django Development Server**
    ```bash
    python manage.py runserver
    ```

2.  **TailwindCSS Watcher** (Compiles CSS in real-time)
    ```bash
    python manage.py tailwind start
    ```

Access the application at `http://127.0.0.1:8000/`.

## Roadmap

I am continuously working to improve Reportary. Here is a glimpse of what is planned for Phase 2 and beyond:

*   **Organization Support**: Hierarchical management for teams and organizations.
*   **Anonymous Reporting**: Workflows to allow external users to submit reports without accounts.
*   **Advanced Permissions**: Granular role-based access control.
*   **Custom Onboarding**: Tailored setup flows for new teams.
*   **Integrations**: Connections with external tools (GitHub, Slack, etc.).

## License

This project is open source.
