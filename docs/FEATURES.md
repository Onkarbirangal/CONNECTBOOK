# CONNECTBOOK – FEATURES SPECIFICATION

### 1. Fully Responsive Mobile-First Architecture (Section 47)
- **Bootstrap 5 Breakpoints:** Explicit optimization for Extra Small (<576px), Small (576–767px), Medium (768–991px), Large (992–1199px), Extra Large (1200–1399px), and XXL (>=1400px).
- **Desktop UI (>= 1200px):** 3-column layout featuring sticky left sidebar, centered news feed (max 680px), and right sidebar with active contacts and friend suggestions.
- **Tablet UI (768px – 1199px):** Right sidebar collapses gracefully to ensure comfortable reading widths; navigation stays accessible via top header.
- **Mobile UI (< 768px):**
  - **Top Header:** Clean compact header featuring brand logo, search icon button, Messenger badge, notification bell, and account dropdown.
  - **Fixed Bottom Navigation:** 6 accessible navigation items (Home, Friends, Videos, Groups, Notifications, Menu) with active indicators and real-time badge counters.
  - **Body Padding Guard:** `body.has-bottom-nav` ensures content is never obscured behind bottom navigation.
  - **Mobile Search Modal:** Full-screen modal with instant debounced search across users, groups, and posts.
  - **Responsive Messenger:** Automatic toggle between full-screen conversation directory and active chat room with mobile Back button.
  - **Responsive Profile Header:** Cover photo scales from 320px down to 180px; avatar centers neatly with negative margins; profile navigation tabs scroll horizontally with smooth touch behavior.
  - **Responsive Modals:** Post composer adapts as a bottom sheet / full-screen on mobile (`modal-fullscreen-sm-down`).
  - **Touch Targets:** Minimum 40px–44px for buttons and interactive controls.
  - **Zero Horizontal Overflow:** Guaranteed on all viewports down to 360px.

### 2. Authentication & Security
- **Dual Identifier Login:** Login using either email address or username.
- **Secure Password Hashing:** Utilizes PBKDF2 with SHA256 password hashing.
- **Session Expiry Management:** "Remember me" option persists session for 14 days; standard sessions expire on browser close.
- **Account Deactivation:** Soft-deactivation hides profile and posts without immediate hard deletion.

### 3. User Profiles
- **Profile Customization:** Profile avatar, cover photo, bio, work, education, current city, hometown, and website.
- **5 Comprehensive Tabs:**
  - *Posts:* Feed of published posts with privacy enforcement.
  - *About:* Structured overview of contact, education, and relationship data.
  - *Friends:* Grid displaying all confirmed friendships with mutual friends counts.
  - *Photos:* Filtered gallery of all post image attachments.
  - *Videos:* Filtered gallery of all post video attachments.

### 4. News Feed & Post Composer
- **3-Column Layout:** Sticky left sidebar, center scrollable feed, and sticky right sidebar.
- **Rich Post Composer:** Modal dialog supporting text, audience selection (Public, Friends, Only Me), and multi-file previews.
- **Privacy Engine:** Automatic query filtering prevents unauthorized users from discovering friends-only or private posts.
- **Post Sharing:** Share any public post directly to user's timeline with reference to original author.

### 5. Facebook Reactions & Comments
- **6 Expressive Reactions:** Like (👍), Love (❤️), Haha (😆), Wow (😮), Sad (😢), Angry (😡).
- **Hover/Click/Touch Reaction Picker:** Animated reaction picker bar supporting desktop hover and mobile touch long-press.
- **Nested Comments:** Multi-level replies with collapsible threads and timestamps.

### 6. Ephemeral Stories (24h)
- **Automatic Expiration:** Stories automatically expire 24 hours after creation (`expires_at > timezone.now()`).
- **Media Support:** Text stories with gradient backgrounds, image stories, and video stories.
- **Story Viewer Modal:** Full-screen viewer with animated progress bars, previous/next slide navigation, and view tracking.

### 7. Messenger & Real-Time Chat
- **1-on-1 and Group Chats:** Private chats with friends.
- **WebSocket Connection:** Instant message delivery using Daphne and Django Channels.
- **Typing Indicators:** Real-time feedback when partner is typing.
- **HTTP Fallback:** Automatic polling fallback if WebSockets are interrupted.

### 8. Real-Time Notifications
- **Toast Alerts:** Non-intrusive floating toasts on top right.
- **Notification Dropdown:** Navbar badge showing unread count with quick action list.
- **Notification Page:** Full history with mark-all-read and deletion.

### 9. Communities & Groups
- **Public & Private Groups:** Instant join for public groups; approval-based join requests for private groups.
- **Group Timelines:** Dedicated post composer and discussion feed per group.

### 10. Video Discovery & Reels
- **Video Feed:** Dedicated hub for video content and short-form media playback.

### 11. Saved Items & Memories
- **Bookmark System:** Save posts to a personal library.
- **On This Day:** Discover historical posts created on the same calendar day in past years.

### 12. Admin & Moderation
- **Executive Dashboard:** 7-day registration and posting trends, user counts, and active ratios.
- **Moderation Queue:** Inspect user reports, delete violating content, and review decisions.
- **Audit Logging:** System logs for administrative changes and moderation actions.

### 13. Pages Module (`/pages/`)
- **Page Management:** Create, customize, and edit public entity pages (Business, Creator, Community, Organization).
- **Page Follow System:** Users can follow pages to receive updates in their primary news feed.
- **Page Timelines:** Page admins can post directly as the page, with media attachments, reactions, and nested comments.
- **Page Analytics (`/pages/<slug>/analytics/`):** Real-time metrics tracking total followers, post count, aggregate reactions, and comments.

### 14. Events Module (`/events/`)
- **Event Scheduling:** Create public or private events with dates, times, venue locations, descriptions, and cover banners.
- **Interactive RSVPs:** Going, Interested, and Not Going statuses with instant counter updates.
- **Attendee Roster:** View profiles of all confirmed attendees.

### 15. Marketplace Module (`/marketplace/`)
- **Local Commerce:** Peer-to-peer buy and sell classifieds across Electronics, Vehicles, Home & Garden, Apparel, and Sports.
- **Filters & Search:** Real-time price range (min/max), category dropdown, and keyword search.
- **Buyer-Seller Inquiries:** Direct messaging inquiry button prefilled with the listing's details.
- **Status Lifecycle:** Mark items as Available, Sale Pending, or Sold.

### 16. Live Streaming Studio (`/live/`)
- **Broadcasting Architecture:** Scheduled broadcast calendar and real-time live studio room preview.
- **Broadcaster Controls:** Start and End broadcast buttons with automated state transitions (Scheduled, Live, Ended).
- **Studio Preview:** Simulated live player, active viewer counter, stream key management, and simulated real-time chat.
- **Compliance Tagging:** Explicitly labeled as a preparation/preview studio without claims of unverified third-party hardware encoders.

### 17. User Privacy Center (`/settings/privacy/`)
- **Granular Controls:** Field-level profile visibility (Public, Friends Only, Only Me), default post audience selector, 24h story privacy, friend request permissions (Everyone vs. Friends of Friends), messaging permissions, search discoverability toggle, online active status toggle, and read receipts.
- **Enforced Security:** Zero frontend-only hiding; privacy rules are strictly enforced in backend ORM queries, serializers, and views.

### 18. Account Security & Data Control (`/settings/security/` & `/settings/your-information/`)
- **Active Device Sessions:** Real-time list of all authenticated devices, IP addresses, browser agents, and timestamps.
- **Remote Session Revocation:** One-click termination of all other sessions with immediate invalidation in Django's session store.
- **Machine-Readable Data Export:** Complete JSON archive download containing user profile, posts, comments, media links, and friends list.
- **Scheduled Deletion Safeguards:** 14-day grace period for account deletion requests with password re-authentication and user cancellation.

