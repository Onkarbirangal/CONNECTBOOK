# ConnectBook V5 – Complete Facebook-Style Advanced Post Creation System
## Architecture, Models, Composer & Performance Guide

---

## 1. Executive Summary

ConnectBook V5 introduces a production-grade, Facebook-inspired post creation, delivery, and management architecture. Engineered on **Django 5.2**, **Channels ASGI**, and modern **Vanilla ES6 JavaScript**, ConnectBook V5 provides rich social publishing without introducing third-party frontend frameworks or resetting the existing database.

---

## 2. Advanced Post Composer Architecture

### 2.1 Composer Interface Overview
The composer is implemented in `templates/includes/post_composer_modal.html` and triggered seamlessly across the feed, profiles, groups, and post management pages.

- **Dynamic Identity Header**: Displays author avatar, display name, and dynamic badges for feeling/activity, location, and tagged companions.
- **Audience & Privacy Selector**:
  - `Public`: Anyone on or off ConnectBook can view.
  - `Friends`: Visible exclusively to accepted friends.
  - `Friends except...`: Hides post from specific selected friends (`custom_audience_deny`).
  - `Specific friends`: Visible only to explicitly selected friends (`custom_audience_allow`).
  - `Only me`: Private post visible only to the author.
  - `Custom`: Granular audience rules with explicit allow and deny lists.
- **Dynamic Colored Text Background Presets**:
  - Automatically enabled for text-only posts; reverts to standard clean card when media or polls are attached.
  - 7 Presets: Sunset (`grad_sunset`), Ocean (`grad_ocean`), Fire (`grad_fire`), Royal Purple (`grad_purple`), Emerald (`grad_emerald`), Dark Mode (`grad_dark`), Love Gradient (`grad_love`).
- **Multi-Photo & Video Upload Area**:
  - Drag-and-drop or file picker for multiple image and video attachments.
  - Live thumbnail preview cards with per-image caption and alt-text accessibility inputs.
  - Individual remove buttons per attachment.
- **Feeling & Activity Picker**:
  - Structured categories: *Feelings*, *Celebrating*, *Watching*, *Eating*, *Listening to*, *Drinking*.
  - Live emoji indicators (e.g. `😊 Happy`, `🥳 Celebrating`, `🍕 Eating`, `🎧 Listening to`).
- **People Tagging**:
  - Real-time debounced AJAX search endpoint (`/posts/tag-search/?q=...`).
  - Excludes author and blocked users.
  - Interactive pill tags with instant removal.
  - Generates notifications for all tagged users upon publication.
- **Location Check-In**:
  - Location name and street/city address fields.
  - Renders red location pin badge in feed card header.
- **Milestone & Life Event Creator**:
  - Allows marking milestone events (e.g., "Started New Job at Tech Corp", "Graduated University").
  - Renders stylized golden milestone banner in the feed card.
- **SSRF-Protected Link Preview Scraper**:
  - Real-time link scraper (`/posts/link-preview/?url=...`).
  - Scrapes OpenGraph `og:title`, `og:description`, `og:image`, and standard HTML meta tags.
  - **SSRF Security Protection**: Strictly rejects `localhost`, `127.0.0.1`, loopbacks, and private IP blocks (`10.*`, `192.168.*`, `172.16-31.*`).
- **Interactive Poll Generator**:
  - Supports 2 to 5 dynamic voting options.
  - Expiration settings: 1 day, 3 days, 7 days, 14 days, or no expiration.
- **Scheduling & Draft Controls**:
  - Date and time picker for future publishing (`scheduled_at`).
  - "Save Draft" button to store unreleased drafts.

---

## 3. Post Feed & Engagement Architecture

### 3.1 Feed Card Extensions (`templates/includes/post_card.html`)
- **Header Badges**: Author line incorporates feeling emoji, location pin, and tagged friend links.
- **Styled Background Content**: Renders 240px card with centered 22px bold text for styled posts.
- **Interactive Polls**: Real-time progress percentage bars, vote count recalculation via AJAX.
- **Link Previews**: Displays thumbnail image, domain, title, and excerpt with clickable external redirect.
- **Fullscreen Facebook Lightbox Gallery**:
  - Clicking any post image opens `templates/includes/lightbox_modal.html`.
  - Next/Previous image cycling, keyboard arrow keys navigation (`ArrowLeft`, `ArrowRight`, `Escape`).
  - Image counter (`Image 1 of 4`), image caption display, and high-res image download button.
- **Reactions Suite**: Full Facebook 7-reaction set:
  - 👍 `Like` | ❤️ `Love` | 🥰 `Care` | 😆 `Haha` | 😮 `Wow` | 😢 `Sad` | 😡 `Angry`
- **Post Insights Modal**:
  - Available to post author via `View Insights` in dropdown menu.
  - Displays Unique Reach (via `PostView`), Total Impressions, Engagement Rate %, Reactions breakdown, Comments count, and Shares count.

---

## 4. Post Management Dashboard (`/my-posts/`)

Located at `/my-posts/` and accessible from the top navigation and left sidebar.

### 4.1 Dashboard Tabs
1. **Published**: Active posts on user timeline and newsfeed.
2. **Drafts**: Saved unreleased drafts with one-click edit and publish controls.
3. **Scheduled**: Posts queued for future publication with live countdown.
4. **Archived**: Hidden posts archived from the timeline.
5. **Trash**: Soft-deleted posts stored in a 30-day recycling bin:
   - `Restore Post`: Immediately reinstates post to timeline and feeds.
   - `Delete Permanently`: Irreversibly purges the post record and attached media files.
6. **Saved Posts**: Quick access to bookmarked community posts.

---

## 5. Database Schema & Models

### 5.1 `Post` Model
- `post_type`: 20 choices including `text`, `photo`, `multiple_photo`, `video`, `poll`, `milestone`, `feeling`, `link`, etc.
- `background_style`: `none`, `grad_sunset`, `grad_ocean`, `grad_fire`, `grad_purple`, `grad_emerald`, `grad_dark`, `grad_love`.
- `feeling_category`, `feeling_text`, `feeling_icon`: Feeling and activity metadata.
- `location_name`, `location_address`: Check-in coordinates and metadata.
- `link_url`, `link_title`, `link_description`, `link_image`: Link preview OpenGraph data.
- `tagged_users`: Many-to-Many relationship with `User`.
- `custom_audience_allow`, `custom_audience_deny`: Many-to-Many relationships for granular privacy.
- `allow_sharing`: Boolean flag controlling post sharing.
- `milestone_title`: Milestone banner title.
- `is_trashed`, `trashed_at`: Two-tier soft delete and recovery tracking.

### 5.2 `PostMedia` Model
- `caption`: Per-media caption.
- `alt_text`: Accessibility screen-reader text.
- `location`: Per-media location tag.

### 5.3 `PostView` Model
- `post`: Foreign key to `Post`.
- `viewer`: Foreign key to `User` (optional for anonymous/guest views).
- `ip_address`: Viewer client IP address.
- `viewed_at`: Timestamp for analytics aggregation.

---

## 6. Security & Performance Safeguards

1. **SSRF Defense**: Strict validation of target host and resolution before fetching link preview metadata.
2. **Block Compliance**: Blocked users are suppressed from user tagging search and cannot view restricted posts.
3. **Debounced View Tracking**: Frontend `IntersectionObserver` triggers `/posts/<id>/record-view/` once per post per session when scrolled into view >= 50% for at least 1 second.
4. **Data Integrity**: Full database backup preserved at `db.sqlite3.v5_20261124.bak`.
