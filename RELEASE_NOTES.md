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
