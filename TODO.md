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

## ☐ 19. Better Report Workflow

> Complete the report lifecycle.

### Report Actions

- [ ] Edit report
- [ ] Delete report (permissions)
- [ ] Duplicate report detection
- [ ] Bookmark reports
- [ ] Watch/Follow reports

### Content Improvements

- [ ] Markdown support
- [ ] Rich text preview
- [ ] Better attachment uploader
- [ ] Drag & drop upload

---

## ☐ 20. Search Improvements

> Search should be powerful enough for real projects.

### Global Search

- [ ] Search reports
- [ ] Search projects
- [ ] Search comments
- [ ] Search organizations

### Filters

- [ ] Status
- [ ] Severity
- [ ] Assignee
- [ ] Reporter
- [ ] Organization
- [ ] Components
- [ ] Date range

### Extra

- [ ] Saved searches
- [ ] Recent searches

---

## ☐ 21. Project Dashboard

> Every project deserves its own overview.

### Overview

- [ ] Project statistics
- [ ] Recent activity
- [ ] Recent reports
- [ ] Active collaborators
- [ ] Project health summary
- [ ] Tasks

---

## ☐ 22. User Experience Improvements

> Small improvements that make the application feel polished.

### UI

- [ ] Better empty states
- [ ] Loading skeletons
- [ ] Toast notifications
- [ ] Improved mobile responsiveness
- [ ] Keyboard shortcuts
- [ ] Better dark mode

---

## ☐ 23. Attachments & Media

> Improve report evidence handling.

- [ ] Multiple attachments
- [ ] Image previews
- [ ] Download attachments
- [ ] File validation
- [ ] File size limits

---

## ☐ 24. Developer Platform

> Prepare Reportary for future integrations.

### API

- [ ] Basic REST API
- [ ] API tokens
- [ ] API documentation

### Future

- [ ] Webhooks foundation

---

## ☐ 25. Administration

> Better control for administrators.

### Admin

- [ ] User management
- [ ] Organization management
- [ ] Project moderation
- [ ] Report moderation
- [ ] Site announcements
- [ ] Allow users to delete their account

---

## ☐ 26. Launch Readiness

> Polish everything before the public announcement.

### Product

- [ ] Demo project
- [ ] Demo reports
- [ ] Landing page improvements
- [ ] FAQ page
- [ ] Documentation
- [ ] Privacy Policy
- [ ] Terms of Service
- [ ] Contact page

### Deployment

- [ ] Custom domain
- [ ] Production deployment
- [ ] Performance optimization
- [ ] Accessibility review

### Testing

- [ ] Internal testing
- [ ] Beta testing (10–20 users)
- [ ] Fix critical issues
- [ ] Production checklist

---

# Not Yet (Future Versions)

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

---

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

---

# 🚀 Stable Launch

Once everything above is complete:

- Public announcement
- LinkedIn launch
- Community showcase
- Open beta feedback
- Begin versioning (`v1.0.0`)