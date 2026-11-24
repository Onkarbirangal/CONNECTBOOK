# CONNECTBOOK V4 — VIDEO POST SYSTEM SPECIFICATION

## Overview
ConnectBook V4 introduces a real, production-ready video ecosystem designed for both long-form creator videos and short-form Reels.

---

## 1. Architecture & Data Models

### Video Model (`social.models.Video`)
- **Fields**:
  - `author`: ForeignKey to `User`
  - `title`: CharField(max_length=200)
  - `description`: TextField(blank=True)
  - `video_file`: FileField(upload_to='videos/%Y/%m/')
  - `thumbnail`: ImageField(upload_to='videos/thumbnails/%Y/%m/', null=True, blank=True)
  - `category`: Choices (`entertainment`, `gaming`, `education`, `music`, `tech`, `lifestyle`, `sports`, `news`)
  - `privacy`: Choices (`public`, `friends`, `private`)
  - `duration`: PositiveIntegerField (seconds)
  - `views_count`: PositiveIntegerField(default=0)
  - `processing_status`: Choices (`processing`, `ready`, `failed`)
  - `created_at`, `updated_at`: DateTimeFields

### Engagement & Storage Models
- `VideoView`: Tracks unique views, viewing user, IP address, watch time, and timestamps.
- `VideoReaction`: Unique per-user reactions (`like`, `love`, etc.).
- `VideoComment`: Threaded comments with parent-child hierarchy.
- `SavedVideo`: Bookmark videos to custom collections.

---

## 2. Custom Video Player Features

The video detail view (`/videos/<video_id>/`) is powered by an interactive HTML5 custom player with:
- **Play / Pause toggle**: Direct click on canvas or controls bar.
- **Scrubber bar**: Smooth interactive timeline seeking.
- **Volume & Mute toggle**: Real-time gain control.
- **Playback Speed Selector**: 0.5x, 0.75x, 1x (Normal), 1.25x, 1.5x, 2x speeds.
- **Fullscreen Mode**: Cross-browser Fullscreen API support.
- **Related Videos Sidebar**: Filtered by category and creator for continuous discovery.

---

## 3. Short Video (Reels) System

### Reel Model (`social.models.Reel`)
- **Vertical Aspect Ratio**: 9:16 mobile-first video viewer at `/reels/`.
- **Autoplay with IntersectionObserver**: Reels automatically play when scrolled into viewport and pause when out of view.
- **Audio Sound Toggle**: Tap anywhere on the reel stage to mute or unmute audio.
- **Action Sidebar**: Real-time Likes, Comments modal, Save bookmark, and Share link copying.
- **Audio Attribution**: Display track title with animated music note badge.

---

## 4. Video Ingestion & Processing

1. **Upload Validation**: Client and server validation restrict video files to `.mp4`, `.webm`, and `.mov` up to 100MB for long-form and 50MB for Reels.
2. **FFmpeg Integration**: When `ffmpeg` is available on the host machine, automatic thumbnail extraction and duration probing can be invoked via `ffprobe` / `ffmpeg -ss 00:00:01 -i input.mp4 -vframes 1 thumbnail.jpg`.
3. **Graceful Fallback**: If FFmpeg is not installed, the platform uses client-supplied thumbnails or elegant SVG placeholders (`/static/images/default-cover.svg`).
