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


## **Phase 2.0 : Trust & Structure**

> Phase 2 focuses on strengthening the core foundation of Reportary by making users, actions, and access clear, traceable, and reliable. and fixes minor errors from last stage.



## ☐ 11. User & Identity Foundation
> Complete the user model with stable roles

- [] Add developer role during onboarding
- [] User profile page (view & edit basic info)
- [X] Proper logout & session handling

---

## ☐ 12. Report History & Audit Logs
> Report History and change logs should be displayed properly.

- [] Introduce report history / change log model
- [] Track who changed what and when
- [] Display change history to appropriate users

---

## ☐ 13. Basic Organization Support
> Implement basic org app and model for handleing organisations.

- [] Add organization model (minimal)
- [] Support org-owned projects
- [] Add users to organizations
- [] Scope access based on org membership

---
