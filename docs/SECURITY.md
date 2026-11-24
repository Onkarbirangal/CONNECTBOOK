# CONNECTBOOK – SECURITY IMPLEMENTATION

### 1. Cross-Site Request Forgery (CSRF) Protection
- All mutating HTTP requests (POST, PUT, DELETE) require a valid `csrfmiddlewaretoken`.
- AJAX requests pass the CSRF token via `X-CSRFToken` request headers derived from browser cookies.

### 2. Cross-Site Scripting (XSS) Prevention
- Django templates automatically escape HTML content tags.
- Client-side DOM creation functions employ HTML escaping helpers (`escapeHtml`) to sanitize dynamic chat text.

### 3. Password Security & Storage
- Passwords are never stored in plaintext.
- ConnectBook uses the `PBKDF2PasswordHasher` with SHA256 iterations as validated by Django's authentication framework.
- Password change sessions invoke `update_session_auth_hash` to prevent session hijacking.

### 4. Object-Level Permissions
- **Edit & Delete Guards:** Only the author of a post or comment can edit it; non-owners receive `HTTP 403 Forbidden`.
- **Feed & Profile Visibility:** The custom `can_view(user)` method on `Post` enforces public, friends-only, and self-only privacy checks at the model layer.
- **Group Isolation:** Private groups restrict discussion timelines to confirmed members.

### 5. Media Validation & Upload Limits
- Upload sizes are limited to 50MB (`DATA_UPLOAD_MAX_MEMORY_SIZE = 52428800`).
- Content types are checked against MIME classifications (images and videos only).

### 6. Administrative Access Control
- Staff dashboards are protected by `@staff_required` (`user.is_staff or user.is_superuser`).
- Moderation operations (content deletion, account suspension) log actor metadata to the immutable `AuditLog` table.
