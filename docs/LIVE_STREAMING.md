# CONNECTBOOK V4 — LIVE STREAMING SYSTEM SPECIFICATION

## Overview
ConnectBook V4 implements a professional live broadcasting ecosystem with dual operational modes:
1. **In-Browser Broadcaster Studio**: Real-time webcam and microphone preview with live chat and viewer monitoring.
2. **External Streaming Software Support**: Direct RTMP and WHIP ingestion compatibility for OBS Studio, vMix, and Streamlabs.

---

## 1. Data Models (`streaming.models`)

- **`LiveStream`**:
  - `host`: Broadcaster user account.
  - `title`, `description`: Stream metadata.
  - `category`: Gaming, Music, Tech & Education, Entertainment, Sports, General.
  - `audience`: Public, Friends Only, Private.
  - `scheduled_start`, `actual_start`, `ended_at`: Broadcast lifecycle timestamps.
  - `status`: `scheduled`, `live`, `ended`.
  - `stream_key`: Unique private UUID token for RTMP ingestion.
  - `viewer_count`, `peak_viewers`: Live viewer metrics.
  - `slow_mode_seconds`: Chat rate-limiting delay.
- **`LiveStreamViewer`**: Active viewer records linked to user session or IP.
- **`LiveStreamChatMessage`**: Persistent live chat messages with soft-delete moderation.
- **`LiveStreamBlockedUser`**: Chat-banned users per stream channel.

---

## 2. Real-Time Chat & Reaction Pipeline

### Django Channels WebSocket (`LiveStreamConsumer`)
- **Route**: `ws/live/<int:stream_id>/`
- **Group**: `live_stream_<stream_id>`
- **Live Viewer Tracking**: Increments when WebSocket connects, decrements when disconnected; broadcasts `viewer_count_update` to the entire room.
- **Real-Time Chat**: Broadcasts `stream_chat_message` with sender avatar, name, host badge, timestamp, and message.
- **Floating Live Reactions**: Interactive floating emoji animations (❤️, 🔥, 👏, 😮, 👍) float upward over the live video player in real time.
- **Chat Moderation**: Broadcaster can click the trash icon on any message to delete it across all connected viewers instantly via `delete_message`.

---

## 3. Dedicated Streaming Infrastructure (MediaMTX / RTMP / WHIP)

ConnectBook is architected with an honest division between application layer and media streaming servers:
- **Application Server (Django / Daphne ASGI on port 8002)**: Handles user authentication, permissions, chat WebSockets, reactions, viewer counting, and scheduling.
- **Streaming Ingestion Server (MediaMTX)**:
  - Open-source, zero-dependency streaming server for RTMP, WHIP, and HLS.
  - Local RTMP Ingestion: `rtmp://localhost:1935/live/<stream_key>`
  - WHIP WebRTC Ingestion: `http://localhost:8554/live/<stream_key>/whip`
  - HLS Playback Delivery: `http://localhost:8888/live/<stream_key>/index.m3u8`

### How to Run MediaMTX Locally
1. Download `mediamtx_vX.Y.Z_windows_amd64.zip` from GitHub.
2. Extract and run `mediamtx.exe`.
3. Configure OBS Studio:
   - **Service**: Custom...
   - **Server**: `rtmp://localhost:1935/live/`
   - **Stream Key**: Paste private key from your ConnectBook Studio dashboard.
4. Viewers on ConnectBook will receive the low-latency HLS or WebRTC playback.
