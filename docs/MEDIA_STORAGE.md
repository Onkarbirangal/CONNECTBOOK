# CONNECTBOOK V4 — MEDIA STORAGE & PROCESSING

## Overview
ConnectBook V4 manages file system storage, file validation, security controls, and upload directories for images, videos, audio, and attachments.

---

## 1. Directory Structure

All media files are stored under the project `media/` directory:
```
media/
├── avatars/               # User profile avatars
├── covers/                # Profile banner covers
├── group_covers/          # Group banner images
├── page_covers/           # Page banner images
├── event_covers/          # Event covers
├── posts/                 # Feed post images and video attachments
├── stories/               # 24-hour disappearing stories
├── marketplace/           # Marketplace product photos
├── videos/                # Long-form video posts (%Y/%m/)
│   └── thumbnails/        # Video poster images
├── reels/                 # Vertical short reels (%Y/%m/)
│   └── thumbnails/        # Reel poster frames
└── livestreams/           # Broadcast thumbnails and recordings
```

---

## 2. File Validation & Quotas

- **Images**: `.jpg`, `.jpeg`, `.png`, `.webp`, `.gif` (up to 10MB).
- **Long-Form Videos**: `.mp4`, `.webm`, `.mov` (up to 100MB).
- **Reels**: `.mp4`, `.webm`, `.mov` (up to 50MB, max recommended 90s).
- **MIME Probing**: Validates file extension and binary headers to prevent arbitrary file upload vulnerabilities.
