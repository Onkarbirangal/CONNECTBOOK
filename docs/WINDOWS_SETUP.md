# CONNECTBOOK V4 — WINDOWS 11 DEVELOPMENT SETUP

## Overview
ConnectBook V4 runs seamlessly on Windows 11 using Python 3.12, Django 5.2, Django Channels ASGI, and SQLite.

---

## 1. Prerequisites
- **Python**: 3.12 64-bit on PATH
- **Git** (optional for version control)
- **PowerShell 7+** or Windows PowerShell

---

## 2. Running the Development Server on Port 8002

Because ConnectBook utilizes real-time WebSockets (Live streaming, Messenger chat, WebRTC signaling), the application must be served using an **ASGI** server such as **Daphne**.

```powershell
# From the project root directory:
cd C:\Users\onkar\OneDrive\Documents\Antigravity\first

# Start Daphne ASGI server on port 8002
daphne -b 127.0.0.1 -p 8002 connectbook.asgi:application
```

Alternatively, during standard development:
```powershell
python manage.py runserver 8002
```

---

## 3. Running Database Migrations & Automated Tests

```powershell
# Verify system check:
python manage.py check

# Run all automated tests:
python manage.py test

# Run specific app test suite:
python manage.py test chat streaming social admin_dashboard
```

---

## 4. Default Ports & Endpoints
- **Web Application**: `http://localhost:8002/`
- **Admin Dashboard**: `http://localhost:8002/admin-panel/`
- **Django Admin**: `http://localhost:8002/admin/`
- **WebRTC Signaling**: `ws://localhost:8002/ws/call/<room>/`
- **Live Stream Chat**: `ws://localhost:8002/ws/live/<stream_id>/`
- **Messenger Chat**: `ws://localhost:8002/ws/chat/<conv_id>/`
