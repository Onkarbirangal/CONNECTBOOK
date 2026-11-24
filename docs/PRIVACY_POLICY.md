# ConnectBook Privacy Policy & Data Protection Guide

**Effective Date:** November 2026  
**Version:** 3.0 Enterprise  
**Applies to:** ConnectBook Social Networking Platform  

---

## 1. Introduction

ConnectBook ("Connect with Friends. Share Your World") is committed to transparent, privacy-first social networking. This policy explains what information is collected, how it is processed, user rights, and security safeguards built directly into the platform.

---

## 2. Information We Collect

1. **Account Registration Data:**
   - Full name, unique username, verified email address, date of birth, gender.
   - Hashed passwords using Django's PBKDF2 with SHA-256 algorithm.
2. **Profile & User Content:**
   - Bio, city, hometown, workplace, education, relationship status, avatar, and cover photo.
   - Text posts, shared posts, media files (photos and videos), stories, and comments.
3. **Connections & Interactions:**
   - Friendships, friend requests, following relationships.
   - Post reactions, message reactions, comments, and replies.
4. **Usage & Device Metadata:**
   - Client IP addresses, browser user-agent strings, and device session timestamps logged in `UserSessionRecord` to detect unauthorized account access.

---

## 3. Granular Privacy Controls

Users maintain full control over their content through `/settings/privacy/`:

- **Profile Visibility:** Choose between Public, Friends Only, or Only Me.
- **Post Default Audience:** Default visibility applied to newly composed posts.
- **Story Privacy:** Restrict ephemeral 24-hour stories to Friends Only.
- **Tagging & Mention Permissions:** Specify who can tag you in posts or mention you in comments (Everyone, Friends Only, or No One).
- **Search Discoverability:** Opt-in or opt-out of appearing in global user search suggestions.
- **Active Status & Read Receipts:** Toggle visibility of real-time presence indicators and message read states.

---

## 4. Account Restrictions & Safety Tools

1. **Blocking (`BlockedUser`):**
   - Blocked accounts cannot see your posts, view your profile, send messages, or send friend requests.
2. **Restricting (`RestrictedUser`):**
   - Restricted accounts only see your public posts. Their presence is hidden from your online status.
3. **Muting (`MutedUser`):**
   - Silences all notifications triggered by specific accounts without notifying them.

---

## 5. User Data Portability & Account Deletion

ConnectBook complies with data protection principles (GDPR/CCPA alignment) via `/settings/your-information/`:

1. **JSON Data Portability Export:**
   - One-click machine-readable JSON download including user account details, profile, friend list, posts, comments, and media URLs.
2. **14-Day Grace Period Account Deletion:**
   - Users may request account deletion with password verification.
   - A 14-day grace period is enforced, during which the user may cancel the deletion at any time from their settings page.
