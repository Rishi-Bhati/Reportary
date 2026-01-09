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
