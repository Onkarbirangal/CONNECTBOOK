# CONNECTBOOK V6 UPGRADE GUIDE
## Complete Facebook-Style Profile, Posts, Photos, Videos, Reels, Stories & Store Upgrade

ConnectBook V6 delivers a massive architectural and experiential upgrade, establishing complete parity with modern Facebook user experience across profiles, multimedia galleries, vertical video reels, ephemeral stories, creator analytics, and community marketplace commerce.

---

## 1. Complete User Profile System (`/profile/<username>/`)

### Header & Identity
- **Cover Photo & Avatar Modals**: Instant photo uploads with preview and modal dialogs (`update_avatar`, `update_cover`).
- **Profile Lock Security**: Authentic Facebook feature allowing users to toggle "Profile Lock" (`toggle_profile_lock`). When locked, non-friends cannot view full details or private media.
- **Verification & Badges**: Verified checkmark badge for notable profiles.
- **Audience & Stats Bar**: Friends count, Followers count, Following count, Mutual friends counter, Intro, Bio, Education, Work, Website, and Location.
- **Action Controls**: Add Friend, Accept Request, Cancel Request, Follow/Unfollow, Direct Message, Edit Profile, Share Profile, and Lock Profile.
- **Story Highlights Bar**: Circular highlights viewer embedded directly below the profile header.

### 11 Functional Profile Tabs
1. **Posts**: User's published timeline posts with V5 Composer trigger (for profile owner), pinned posts, and post cards.
2. **About**: Complete personal info divided into Overview, Work & Education, Places Lived, Contact & Basic Info, Family & Relationships, and Details About You.
3. **Friends**: Grid of confirmed friends with mutual friend counts; respects privacy setting (`friends_list_visibility`).
4. **Photos**: Multi-subsection gallery:
   - *Your Photos*: All photos uploaded by the user across posts and albums.
   - *Photos of You*: Photos where the user is tagged.
   - *Albums*: Visual cards for all user albums (`PhotoAlbum`) with photo counters and covers.
5. **Videos**: Grid of published videos with duration badges and view counts.
6. **Reels**: Grid of 9:16 vertical reels with view badges and quick watch buttons.
7. **Stories**: Active 24-hour stories plus permanent highlights.
8. **Check-ins**: Map pins and location check-ins from user posts.
9. **Likes**: Posts and content reacted to by the user.
10. **Saved**: Private bookmarks repository strictly visible to the profile owner only.
11. **More**: Marketplace listings by user and Creator Studio quick access.

---

## 2. Photos & Albums Management

- **Models**: `PhotoAlbum` and `AlbumPhoto` with timestamps, captions, alt-text, and privacy settings.
- **Album Actions**:
  - Create Album (`/albums/create/`) with title, description, and privacy selector.
  - Multi-Photo Upload (`/albums/<id>/upload/`) supporting batch drag-and-drop.
  - Album Detail View (`/albums/<id>/`) with responsive photo grid and fullscreen lightbox integration.
  - Edit Album (`/albums/<id>/edit/`) and Delete Album (`/albums/<id>/delete/`).
  - Delete Photo (`/albums/photos/<id>/delete/`).

---

## 3. Reels Creation & Vertical Scroll-Snap Feed

- **Creation & Recording (`/reels/create/`)**:
  - Dual-mode: File upload or **Live Web Camera Recorder** using HTML5 `getUserMedia` and `MediaRecorder` API.
  - Real-time 9:16 video preview canvas.
  - Caption, audio title, location check-in, tagged friends, audience privacy selector.
  - Comments toggle and sharing toggle.
  - Draft or Publish status.
- **Vertical Feed (`/reels/`)**:
  - Fullscreen 9:16 vertical scroll-snap feed matching Facebook Reels.
  - `IntersectionObserver` auto-play engine (only active visible reel plays; others pause and mute).
  - Floating action sidebar: Like/React, Comments drawer, Share, Save, and Follow author.
  - **Infinite Scroll Feed API (`/reels/api/feed/?page=N`)**: Asynchronous JSON pagination for endless vertical scrolling without full-page reloads.

---

## 4. Stories System & Highlights

- **Story Composer (`/stories/create/`)**:
  - Photo, Video, and Text story modes.
  - Real-time preview canvas with 6 background gradients for text stories.
  - Location tag, friends tag, and audience privacy selector (Public, Friends, Only Me).
  - Auto-expiration after 24 hours.
- **Viewer & Interaction (`templates/base.html` & `static/js/stories.js`)**:
  - Feed stories carousel at the top of the timeline.
  - Fullscreen story viewer with multi-segment progress timer.
  - Floating bottom reaction emojis (👍, ❤️, 🥰, 😆, 😮, 😢, 😡) saving to `StoryReaction`.
  - Direct message reply bar: dispatches a direct chat message via Messenger and logs to `StoryReply`.
- **Highlights (`/stories/highlights/create/`)**:
  - Create themed collections of stories (e.g. "Travel", "Best Moments").
  - Dedicated API (`/stories/highlights/<id>/stories/`) to stream highlight segments in the story viewer.
- **Story Archive (`/stories/archive/`)**:
  - Private archive of all past stories accessible only to the author.

---

## 5. Marketplace Store & Seller Dashboard

- **Multi-Image Listings**: `MarketplaceImage` model allowing sellers to attach up to 8 images per item.
- **Condition Grading**: New, Like New, Good, Fair filters and badges.
- **Buyer Inquiries (`/marketplace/<id>/inquire/`)**:
  - "Contact Seller" modal on listing detail.
  - Creates a `MarketplaceInquiry` record.
  - Dispatches a direct message in ConnectBook Messenger between buyer and seller with item details and price.
- **Seller Dashboard (`/marketplace/seller/dashboard/`)**:
  - Overview KPI cards: Active listings, sold items, total views, and buyer inquiries.
  - Inventory management table with quick actions: Mark as Sold, Edit, Delete.
  - Inquiries inbox with buyer profile, message snippet, and quick link to chat.

---

## 6. Creator Studio & Analytics Hub (`/creator-studio/`)

- **Performance Analytics**:
  - Aggregated Reach & Views: Total views across Videos, Reels, and Posts.
  - Audience Growth: Follower count and live broadcasts.
  - Total Published Media: Count of Videos, Reels, Posts, and Photos.
  - Engagement Rate %: Real-time calculation based on interactions divided by views.
  - Detailed Engagement Breakdown: Total Reactions, Total Comments, Post Shares, and Saved Bookmarks.
- **Date Range Filtering**:
  - All Time, Last 7 Days, Last 30 Days, Last 90 Days.
- **Content Management Tabs**:
  - Videos, Reels, Feed Posts, Photo Albums, Saved Drafts, and Scheduled Posts.

---

## 7. Automated Test Suite

ConnectBook V6 includes 48 automated test cases covering all subsystems:
- `accounts`: User profile tabs (all 11 tabs), profile locking, privacy visibility, follow, block, restrict, mute, data export, and session termination.
- `social`: Posts, reactions, comments, media upload, photo albums CRUD, vertical reels, infinite scroll API, creator studio analytics, link preview SSRF protection, trash lifecycle.
- `stories`: Story creation, reactions API, replies creating chat messages, highlights creation & streaming API, and archive.
- `marketplace`: Listings CRUD, condition filters, multi-images, inquiries dispatching chat messages, and seller dashboard.

Run tests:
```bash
python manage.py test
```
Result: **48 tests, 100% passed (OK)**.
