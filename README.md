# ConnectBook – Connect with Friends. Share Your World.
## Complete Facebook-Style Social Networking Platform with Full-Screen Responsive Engine

ConnectBook is a full-featured, responsive, production-grade Facebook-inspired social networking platform built with **Python 3.12**, **Django 5.2**, **Django Channels (ASGI WebSockets)**, **WebRTC P2P Communication**, and **Bootstrap 5**.

---

## 🌟 What's New in the Responsive Master Release

### 1. 6-Tier Responsive Breakpoint Engine
- **Small Mobile (320px – 374px)**: Ultra-compact navbar with icon brand, 32px touch targets, icon-only bottom navigation, 30px chat actions, and safe-area padding. Zero horizontal scrolling.
- **Standard Mobile (375px – 430px)**: 18px brand text, 34px action icons, 9px bottom navigation labels, edge-to-edge post cards, and horizontal scrollable tab strips (`.cb-feed-tabs`).
- **Large Mobile (431px – 767px)**: Full mobile experience with 36px action icons, 100% viewport width, and adaptive card grids.
- **Tablet (768px – 1023px)**: 2-column card layouts, 240px cover heights, 110px avatars, and 70% chat bubble width.
- **Laptop & Desktop (>= 1024px)**: Existing desktop layout 100% preserved. Left and right sidebars, 3-column feed, and full navigation tabs remain intact.

### 2. Chat Page – Mobile Priority Upgrades
- **Single-Row Chat Header**: Back button, circular avatar with online badge, verified display name, online status ("Active now"), voice call button, video call button, profile button (text on desktop, icon on mobile), and 3-dots dropdown all fit on ONE row without overflow.
- **Full Viewport Body**: Uses remaining available vertical space (`calc(100dvh - var(--cb-nav-height))`) with independent scrolling (`-webkit-overflow-scrolling: touch; overscroll-behavior-y: contain`), preventing whole-page jumps.
- **Fixed Bottom Composer**: Pinned sticky to the bottom with safe-area insets (`env(safe-area-inset-bottom)`), responsive message input, and `visualViewport` resize listener keeping messages and composer visible during mobile keyboard appearance.
- **Bottom Navigation Elimination during Active Chat**: Bottom navigation is cleanly hidden when in active conversation view on mobile, giving full screen height to the chat.

### 3. Bottom Navigation
- 7 equal-width flex tabs (Home, Friends, Watch, Reels, Groups, Notifications, Menu) with notification badges and dynamic body safe-area padding.

### 4. Cross-Application Optimizations
- **Home Feed**: Category tabs scroll horizontally via `.cb-feed-tabs` without vertical stacking.
- **Friends Hub**: Responsive 2-column architecture with mobile horizontal tab pills and responsive card grid.
- **Watch & Videos**: Video categories and feed tabs use `.cb-feed-tabs`.
- **Reels**: Fullscreen 9:16 vertical scroll-snap feed with overlaid mobile action icons.
- **Marketplace**: 2-column mobile grid with compact gaps (`g-2 g-md-4`).
- **Settings & Privacy**: Horizontal scroll navigation tabs across general settings, privacy center, security sessions, and user data control.
- **54 Automated Tests**: 100% pass rate with zero errors or failures.

---

## 🚀 Technology Stack

- **Backend**: Python 3.12, Django 5.2, Django ORM, Django Channels, Daphne ASGI
- **Frontend**: HTML5, CSS3, Bootstrap 5, Bootstrap Icons, Vanilla ES6 JavaScript, WebRTC
- **Database**: SQLite (`db.sqlite3`)
- **Real-time**: Django Channels WebSockets, InMemoryChannelLayer
- **Development Server**: Port 8002

---

## 🏁 Running the Project

1. Activate your virtual environment and install dependencies:
   ```powershell
   pip install -r requirements.txt
   ```
2. Apply database migrations:
   ```powershell
   python manage.py migrate
   ```
3. Run the automated test suite (54 tests):
   ```powershell
   python manage.py test
   ```
4. Start the development server on port 8002:
   ```powershell
   python manage.py runserver 8002
   ```
5. Open your browser:
   - News Feed: `http://127.0.0.1:8002/`
   - Messenger: `http://127.0.0.1:8002/chat/`
   - Friends Hub: `http://127.0.0.1:8002/friends/`
   - Reels Viewer: `http://127.0.0.1:8002/reels/`
   - Watch Videos: `http://127.0.0.1:8002/watch/`
   - User Profile: `http://127.0.0.1:8002/profile/<username>/`
