# CONNECTBOOK V3 — FEATURE GAP ANALYSIS

| Feature Area | Current V2 State | V3 Enterprise Requirement | Action Required |
|---|---|---|---|
| **Social Feed Engine** | Single reverse-chronological feed with basic privacy filtering. | Multi-tab feed (Personalized, Friends, Following, Trending, Latest), ranking algorithm, AJAX pagination. | Implement ranking engine in `social/views.py` and feed navigation tabs. |
| **Post Management** | Immediate publish only; basic edit & delete. | Draft posts, scheduled posts, edit history, comment toggling, post archiving, post pinning. | Add `status`, `scheduled_at`, `is_archived`, `comments_enabled`, `edit_history` to `Post`. |
| **Saved Items** | Single flat list of saved posts. | Categorized collections (e.g. "Favorites", "Articles", "Work"). | Add `collection_name` to `SavedPost` and collection selector. |
| **Messenger** | Text and attachments over WebSockets. | Message reactions, quoted replies, editing, soft deletion, mute conversation, archive conversation. | Add `MessageReaction`, `Message.reply_to`, `ConversationParticipant.is_muted/is_archived`. |
| **Notifications** | Single list, real-time toast push. | Notification categories, individual delete, notification preferences per user. | Expand `Notification.notification_type`, add category filters & preference controls. |
| **Privacy Controls** | Profile visibility, default audience, search discoverability. | Restricted accounts, Muted accounts, tagging permissions, mention permissions. | Add `RestrictedUser`, `MutedUser`, and fields to `UserPrivacySetting`. |
| **Communities** | Groups, Pages, Events core CRUD. | Group rules, pinned announcements, saved marketplace listings. | Add `GroupRule`, `GroupAnnouncement`, `SavedListing`. |
| **Admin Analytics** | 7-day registration chart & basic counters. | Real database-driven user engagement, content distribution, moderation resolution analytics with Chart.js. | Expand `admin_dashboard/views.py` with aggregated metrics. |
| **UI/UX Polish** | Standard Bootstrap 5 cards. | Global search overlay, keyboard navigation, loading skeletons, responsive empty states. | Enhance templates and JavaScript with loading skeletons and accessible shortcuts. |
