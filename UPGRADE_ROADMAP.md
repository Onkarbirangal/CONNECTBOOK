# CONNECTBOOK V4 — UPGRADE ROADMAP

**Goal:** Transform ConnectBook into a full-scale real-time multimedia social media platform with Real Video Posts, Reels, Live Streaming, WebRTC Video Calling, Polls, and Creator Studio.

---

## 🛣️ Implementation Roadmap

### Phase 1: Project Audit & Backup (Completed)
- [x] Create database backup `db.sqlite3.v4_20261124.bak`.
- [x] Audit existing apps, URLs, models, and WebSocket routing.
- [x] Generate `PROJECT_AUDIT.md` and `UPGRADE_ROADMAP.md`.

### Phase 2: Real Video Post System & Custom Video Player
- [ ] Create `Video` and `VideoView` models with category, thumbnail, duration, view counting.
- [ ] Build custom responsive HTML5 video player (play/pause, volume, seek, speed, fullscreen).
- [ ] Build `/videos/` feed, video detail `/videos/<id>/`, upload `/videos/upload/`, search and related videos.

### Phase 3: Reels & Short Video Feed
- [ ] Create `Reel` and `ReelView` models.
- [ ] Build dedicated `/reels/` page with full-screen vertical layout, touch gestures, and `IntersectionObserver` autoplay.
- [ ] Reel interactions: like, comment, share, save, follow creator, view counter.

### Phase 4: Real Live Streaming & Live Chat
- [ ] Upgrade `streaming/models.py` with `LiveStreamViewer`, `LiveStreamChatMessage`, `LiveStreamRecording`.
- [ ] Real-time WebSocket consumer for live chat and live viewer counts.
- [ ] Broadcaster interface (`/live/create/`, `/live/dashboard/`) with browser camera/mic capture and stream key ingestion setup.
- [ ] Viewer interface (`/live/stream/<id>/`) with chat moderation (slow mode, delete, block).

### Phase 5: WebRTC Audio & Video Calling
- [ ] Create `CallSession` and `CallParticipant` models.
- [ ] Implement `CallSignalingConsumer` over Channels WebSocket for SDP Offer/Answer and ICE exchange.
- [ ] Build call initiate button, incoming call modal, and active call interface with media toggles.

### Phase 6: Polls & Interactive Post Composer
- [ ] Create `Poll`, `PollOption`, `PollVote` models with unique database constraint.
- [ ] Add Polls tab to post composer with dynamic options and expiration.
- [ ] Render interactive voting widget with instant percentage calculations.

### Phase 7: Creator Studio & Video Analytics
- [ ] Build `/creator-studio/` with real database-driven analytics (views, watch time estimation, top content).
- [ ] Unified content manager for posts, videos, reels, and streams.

### Phase 8: Explore, Discovery & Admin V4
- [ ] Build `/explore/` discovery page (trending posts, hashtags, reels, videos, creators).
- [ ] Extend `/admin-panel/` with Video, Reel, and Stream moderation controls.

### Phase 9: Migrations, Testing & Verification
- [ ] Generate and apply migrations cleanly.
- [ ] Add comprehensive test suite covering all V4 features.
- [ ] Verify 100% test pass rate with `python manage.py test`.

### Phase 10: Complete V4 Documentation Suite
- [ ] Write dedicated technical guides in `docs/` and update `DEVELOPMENT_STATUS.md` and `README.md`.
