# **Reportary Build Plan**


## The Order Is Important

If you skip and jump around, you’ll confuse yourself and burn out. The correct flow is:

**Projects → Reports → Report Detail → Comments → User Filters → Notifications**

> **DO NOT** jump to orgs, private links, anonymous flow, custom onboarding, etc. That’s all Phase 2 stuff. Right now you need to create the backbone.

---

## **Phase 1: Core Features (The Backbone)**
### ~~☐ 1. Build "Register New Project" Page (DEV ROLE ONLY)~~
> This is the beating heart of your entire platform. Everything else depends on this. You already have the dashboard → "+ New Project" button. Make it functional. 

**A dev must be able to:**
- [x] Create a project
- [x] Set project visibility (public/private)
- [X] Add components
- [X] Add description, logo, and tags
- [X] Auto-generate a slug
- [X] Save the project to the database
- [X] Redirect to the project dashboard upon creation

***Why this first?***
*Because reports cannot exist without a project. Comments cannot exist without reports. Org flows connect to projects. Anonymous links map to projects. Everything downstream depends on this model.*
> This is the beating heart of your entire platform. Everything else depends on this. You already have the dashboard → “+ New Project” button. Make it functional.

---

### ~~☐ 2. Build “Report New Issue” Form (MVP Version)~~
> Not the massive full form you planned earlier. Just a trimmed version to get actual content in the system. Now dashboards will make sense.

**Bare minimum fields to start:**
- [X] Title
- [X] Project
- [X] Steps to Reproduce
- [X] Description / What Happened
- [X] Frequency
- [X] Impact
- [X] Attachments (optional, basic file upload)
- [X] Public/Private toggle

**Actions:**
- [X] Save the new report to the database.
- [X] Redirect to the report detail page.

---

### ~~☐ 3. Build Report Detail Page~~
> This is where the magic happens. Make it clean and readable, as you’ll use this page a LOT while building everything else.

**Should show:**
- [X] Title
- [X] Status
- [X] Severity
- [X] Impact
- [X] Description
- [X] Steps to Reproduce
- [X] Comments Section
- [X] History Log

---

### ~~☐ 4. Build Comments (Basic)~~
> No fancy HTMX, anonymity, or internal notes yet. Just the basic flow to make the app feel alive.

- [X] A user can comment on a report.
- [X] The comment saves to the database.
- [X] The comment shows instantly on the page.

---

### ~~☐ 5. Build Dashboard Filters~~
> These are super easy and quick wins. Just simple queries that will make the dashboard start feeling REAL when combined with reports and comments.

- [X] "Assigned to me" filter
- [X] "Reported by me" filter

---

## **Phase 1.5: Hardening & Access Control (SHORT PHASE)**


### ~~☐ 6. Report Reassignment (Tiny, Optional)~~
> Only if it’s clean and fast.

- [X] Add a simple “Reassign” action
- [X] Only project owner can reassign
- [X] No UI complexity (dropdown + submit)
- [X] No notifications yet

---

### ~~☐ 7. Visibility Enforcement Sweep (Quick Pass)~~
> You already did most of it. Just confirm.
- [X] No private project accessible via direct URL
- [X] No private report accessible via direct URL
- [X] Rules used in views, not only templates

---

### ~~☐ 8. Report Status Lifecycle (Lightweight)~~
>This is the next real feature.

- [X] Add status field (Open / In Progress / Resolved / Closed)
- [X] Only assignee or owner can change status

---

### ☐ 9. ~~Add collaborators features~~
> complete the collaborators feature with all permissions

- [X] Add collaborator in projects models, register project and edit project.
- [X] Collaborators on new project and edit project
- [X] Collaborators cannot reassign reports, but change other things like status etc.
- [X] Basic logic properly implemented

---

### ☐ 10. ~~UI improvements and Beta Launch Ready~~
> make the ui enhancements to make it usable and fix important features

- [X] Improve the UI
- [X] Verify and fix the workflow
- [x] Enable searching features
- [X] Fix all the broken links on UI where href=#

---


## **Phase 2.0 : Trust, Structure and Security**

> Phase 2 focuses on strengthening the core foundation of Reportary by making users, actions, and access clear, traceable, and reliable. and fixes minor errors from last stage.



## ~~☐ 11. User & Identity Foundation~~
> Complete the user model with stable roles

- [X] Add developer role during onboarding
- [X] User profile page (view & edit basic info)
- [X] Proper logout & session handling

---

## ~~☐ 12. Report History & Audit Logs~~
> Report History and change logs should be displayed properly.

- [X] Introduce report and project history / change log model
- [X] Track who changed what and when
- [X] Display change history to appropriate users

--- 

## ~~☐ 13. Basic Organization Support~~
> Implement basic org app and model for handleing organisations.

- [X] Add organization model (minimal)
- [X] Support org-owned projects
- [X] Add users to organizations
- [X] Scope access based on org membership

---

## ~~☐ 14. Basic Security~~
> Implement the most imp very basic layer of security.

- [X] Require users to use strong passwords.
- [X] Show login/password failures in the login/signup card itself.
- [X] Provide each project, report and everything with a UUID instead of default django pk id.
  
---

## ~~☐ 15. Misc.~~
> Minor misc. fixes from last stage...

- [X] Fix the "Search this page" search box and refresh button not working.
- [X] Replace the refresh button to the right of the search box near the search icon.
- [X] Get Started page should ask users to login and then take users to dashboard instead of just showing nota
- [X] Fix hover color contrasts of the "New Project" Button in the sidebar.
- [X] Make the collaborating page and enable the button "Collaborating" in the sidebar to show users the projects they are collaborating (later collaborating reports as well)
- [X] Make a changelog / whats new page shown in the Notification bell for now. (later, it'll be separated)
- [X] Add the critical reports assigned to user or reported on user's projects in the "Needs attention" section. (later, it'll be update based as well)

---


# **Phase 3: Product Readiness & User Experience**

> **Goal:** Transform Reportary from a functional beta into a polished, production-ready platform that teams can confidently adopt.

---

## ~~☐ 16. Notification System~~

> Keep users informed about important events without requiring them to constantly check the dashboard.

### In-App Notifications

- [X] Notification center
- [X] Mark notifications as read/unread
- [X] Notification badges
- [X] Group similar notifications

### Notification Events

- [X] New comment on a report
- [X] Report assigned to user
- [X] Report reassigned
- [X] Report status changed
- [X] Collaborator added
- [X] Organization invitation

---

## ~~☐ 17. Email Integration~~

> Users shouldn't need to keep Reportary open.

### Authentication

- [X] Welcome email
- [X] Email verification
- [X] Password reset email
- [X] Change email confirmation

### Report Updates

- [X] Assignment notification
- [X] Comment notification
- [X] Status update notification
<!-- - [ ] Mention notification (future) -->

### Miscellaneous

- [X] Organization invitation email
<!-- - [ ] Weekly activity digest (optional) -->

---

## ~~☐ 18. Dashboard & Analytics~~

> Make dashboards meaningful.

### Personal Dashboard

- [X] Assigned reports
- [X] Reported reports
- [X] Recently viewed
- [X] Pending actions

### Analytics

- [X] Open vs Closed reports
- [X] Reports by severity
- [X] Reports over time
- [X] Average resolution time
- [X] Reports by component
- [X] Most active projects
- [X] Most active contributors

---

## ~~☐ 19. Better Report Workflow~~

> Complete the report lifecycle.

### Report Actions

- [X] Edit report
- [X] Delete report (permissions)
- [X] Duplicate report detection
- [X] Bookmark reports
- [X] Watch/Follow reports

### Content Improvements

- [X] Markdown support
- [X] Rich text preview
- [X] Better attachment uploader
- [X] Drag & drop upload

---

## ~~☐ 20. Search Improvements~~

> Search should be powerful enough for real projects.

### Global Search

- [X] Search reports
- [X] Search projects
- [X] Search comments
- [X] Search organizations

### Filters

- [X] Status
- [X] Severity
- [X] Assignee
- [X] Reporter
- [X] Organization
- [X] Components
- [X] Date range

### Extra

- [X] Saved searches
- [X] Recent searches

---

## ~~☐ 21. Project Dashboard~~

> Every project deserves its own overview.

### Overview

- [X] Project statistics
- [X] Recent activity
- [X] Recent reports
- [X] Active collaborators
- [X] Project health summary
- [X] Tasks

---

## ~~☐ 22. User Experience Improvements~~

> Small improvements that make the application feel polished.

### UI

- [X] Better empty states
- [X] Loading skeletons
- [X] Toast notifications
- [X] Improved mobile responsiveness
- [X] Keyboard shortcuts
- [X] Better dark mode

---

## ~~☐ 23. Attachments & Media~~

> Improve report evidence handling.

- [X] Multiple attachments
- [X] Image previews
- [X] Download attachments
- [X] File validation
- [X] File size limits

<!-- ---

## ☐ 24. Developer Platform

> Prepare Reportary for future integrations.

### API

- [ ] Basic REST API
- [ ] API tokens
- [ ] API documentation

### Future

- [ ] Webhooks foundation

--- -->

## ~~☐ 24. Administration~~

> Better control for administrators.

### Admin

- [X] User management
- [X] Organization management
- [X] Project moderation
- [X] Report moderation
- [X] Site announcements
- [X] Allow users to delete their account

---

## ~~☐ 25. Launch Readiness~~

> Polish everything before the public announcement.

### Product

- [X] Demo project
- [X] Demo reports
- [X] Landing page improvements
- [X] FAQ page
- [X] Documentation
- [X] Privacy Policy
- [X] Terms of Service
- [X] Contact page

### Deployment

- [X] Custom domain
- [X] Production deployment
- [X] Performance optimization
- [X] Accessibility review

### Testing

- [X] Internal testing
- [X] Beta testing (10–20 users)
- [X] Fix critical issues
- [X] Production checklist

---

<!-- # Not Yet (Future Versions)

These are intentionally postponed until after the stable release.

- [ ] AI report summaries
- [ ] AI duplicate detection
- [ ] Mobile application
- [ ] Desktop application
- [ ] Browser extension
- [ ] Slack integration
- [ ] Discord integration
- [ ] OAuth providers
- [ ] Sprint planning
- [ ] Agile boards
- [ ] Roadmaps
- [ ] Time tracking
- [ ] Gantt charts

--- -->
<!-- 
# Stable Release Checklist

## The product should have:

- [ ] Notifications
- [ ] Emails
- [ ] Dashboard analytics
- [ ] Complete report workflow
- [ ] Better attachments
- [ ] Powerful search
- [ ] Mobile-friendly UI
- [ ] Production deployment
- [ ] Custom domain
- [ ] Documentation
- [ ] Privacy Policy
- [ ] Terms of Service
- [ ] Demo project
- [ ] No known critical bugs

--- -->

# 🚀 Stable Launch

Once everything above is complete:

- Public announcement
- LinkedIn launch
- Community showcase
- Open beta feedback
- Begin versioning (`v1.0.0-beta.1`)


# Phase 3.5: Beta 2 (Community & UX)

> **Goal:** Improve the overall user experience, reduce friction, and introduce the first iteration of public/anonymous reporting.

---

## ~~☐ 26. User Experience Improvements~~

### Authentication

- [X] Add "Show / Hide Password" button on login, signup and password forms.

### Performance & Responsiveness

- [X] Add loading indicators on all actions (button spinner and top progress bar).
- [X] Implement skeleton loaders across the application.
- [X] Load page layout first, fetch content asynchronously.
- [X] Improve navigation responsiveness to make transitions feel instant.

### UI Polish

- [X] Better empty states.
- [X] Toast notifications.
- [X] Improve mobile responsiveness.
- [X] Keyboard shortcuts.
- [X] Improve dark mode consistency.
- [X] UI consistency review across all pages.

---

## ~~☐ 27. Public Report Portals~~

> Allow users to receive reports without exposing their projects.

### Public Reporting Links

- [X] Generate a dedicated public reporting link for every project.
- [X] Allow users to regenerate report links.
- [X] Allow users to disable public reporting links.
- [X] Copy-to-clipboard button for report links.

### Private Project Reporting

- [X] Allow completely private projects to receive reports through public report links.
- [X] Ensure project details remain hidden from anonymous users.

---

## ~~☐ 28. Anonymous Reporting (Basic)~~

> Introduce the first version of anonymous reporting.

### Anonymous Reports

- [X] Allow anonymous users to submit reports.
- [X] Clearly mark anonymous reports.
- [X] Allow project owners to enable/disable anonymous reporting.

### Organization Policies

- [X] Organization-wide toggle for anonymous reporting.
- [X] If disabled at organization level, prevent projects from overriding it.

### Public Links

- [X] Allow anonymous reporting to be enabled/disabled per public reporting link.

### Security

- [X] Add spam protection.
- [X] Add rate limiting.
- [X] Add CAPTCHA / Cloudflare Turnstile.
- [X] Restrict anonymous attachment abuse.

---

## ~~☐ 29. Report Submission Improvements~~

> Make reporting as effortless as possible.

- [X] Improve report submission workflow.
- [X] Better success page after report submission.
- [X] Display report tracking ID after submission.
- [X] Improve attachment experience.
- [X] Review and polish all report forms.

---

# Phase 3.8: Release Candidate (Feature Freeze)

> **No major features beyond this point. Only stability, polish and bug fixes.**

---

## ☐ 30. Release Candidate Preparation

### Product Review

- [ ] Full UI consistency review.
- [ ] Accessibility improvements.
- [ ] Performance review.
- [ ] Mobile responsiveness review.
- [ ] Security review.

Randomize the math question each request (e.g., 7 + 3, 12 - 5, 4 × 2).
Expire the challenge after a few minutes.
Rotate the honeypot field name periodically (e.g., website, homepage, company_site) instead of using an obvious name.
Add a minimum form fill time (e.g., reject submissions completed in under 2–3 seconds), since many bots submit almost instantly.

### Bug Fixes

- [ ] Resolve all critical bugs.
- [ ] Resolve all major UX issues.
- [ ] Resolve all known security issues.

### Documentation

- [ ] Update documentation.
- [ ] Update changelog.
- [ ] Review installation guide.
- [ ] Review deployment guide.

---

# ☐ 31. Stable Launch

> Prepare Reportary for the first stable public release.

### Product

- [ ] Demo project.
- [ ] Demo reports.
- [ ] Landing page improvements.
- [ ] FAQ page.
- [ ] Documentation.
- [ ] Privacy Policy.
- [ ] Terms of Service.
- [ ] Contact page.

### Deployment

- [ ] Custom domain.
- [ ] Production deployment.
- [ ] Performance optimization.
- [ ] Accessibility review.

### Testing

- [ ] Internal testing.
- [ ] Beta testing (10–20 users).
- [ ] Fix critical issues.
- [ ] Production checklist.

---

# 🚀 Stable Release Checklist

The product should have:

- [ ] Fast page navigation.
- [ ] Skeleton loading.
- [ ] Loading indicators.
- [ ] Smooth onboarding.
- [ ] Notifications.
- [ ] Emails.
- [ ] Dashboard analytics.
- [ ] Complete report workflow.
- [ ] Public reporting links.
- [ ] Anonymous reporting (basic).
- [ ] Better attachments.
- [ ] Powerful search.
- [ ] Mobile-friendly UI.
- [ ] Production deployment.
- [ ] Custom domain.
- [ ] Documentation.
- [ ] Privacy Policy.
- [ ] Terms of Service.
- [ ] Demo project.
- [ ] No known critical bugs.

---

# 🚀 Stable Launch

Once everything above is complete:

- Release `v1.0.0`
- Publish GitHub Release
- Publish LinkedIn announcement
- Share on Reddit & Hacker News
- Collect first user feedback
- Begin roadmap for `v1.1.0`