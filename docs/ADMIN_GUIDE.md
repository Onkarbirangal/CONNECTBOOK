# ConnectBook Administrator & Staff Guide

**Access Path:** `/admin-panel/`  
**Authorization:** Staff (`is_staff=True`) or Superuser (`is_superuser=True`)  

---

## 1. Admin Dashboard Overview
The overview dashboard provides real-time database-driven platform analytics:
- **Metric Cards:** Total users, active users, suspended accounts, posts, comments, groups, pages, events, marketplace listings, and live sessions.
- **Growth Chart (Chart.js):** 7-day registration and content publication velocity computed from `db.sqlite3`.
- **Distribution Chart:** Visual community breakdown across modules.

---

## 2. Community Moderation Queue
Access the moderation queue at `/admin-panel/moderation/`:
- Review user-submitted reports for posts, comments, pages, groups, and events.
- **Take Action:** 
  - **Resolve & Remove:** Permanently deletes the violating content and marks report resolved.
  - **Dismiss:** Marks report dismissed when no policy violation occurred.
- **Bulk Moderation:** Check multiple pending reports and apply "Dismiss" or "Resolve & Remove" in one click.

---

## 3. Privacy & Compliance Center
Access compliance records at `/admin-panel/privacy-security/`:
- **Role Permission Audits:** View staff privileges and superuser status. Prevents staff privilege escalation.
- **Account Deletion Requests:** Review and approve or reject 14-day scheduled user deletion requests.
- **Sensitive Access Logging:** When staff inspect sensitive user records, access must be documented with a formal reason, logged to `SensitiveAccessLog` and `AuditLog`.
- **Audit Logs:** Immutable audit log tracking administrative and security events.
