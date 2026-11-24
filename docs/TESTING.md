# CONNECTBOOK V4 – COMPREHENSIVE AUTOMATED TESTING SPECIFICATION

## 1. Test Suite Architecture
The test suite validates core authentication, user privacy settings, friendship workflows, media publishing, WebRTC video calling, real-time live streaming, polls, creator studio, and administrative moderation.

### Test Coverage Across Apps:
- `accounts/tests.py`: User registration signals, profile avatar updates, blocking, privacy settings.
- `chat/tests.py`: Direct messaging, threaded replies, reactions, edit/soft-delete, mute/archive, and **V4 WebRTC calling signaling & call session authorization**.
- `streaming/tests.py`: Broadcast scheduling, start/end lifecycle, **V4 Broadcaster Studio permissions, viewer chat moderation**.
- `social/tests.py`: Post privacy scopes, reaction pickers, draft posts, comments toggling, **V4 Polls voting calculation, Video uploads, Reel interactions, Creator Studio, and Explore discovery**.
- `admin_dashboard/tests.py`: Staff access control, sensitive audit logging, account deletion requests, **V4 Video & Reel moderation, Live Stream forced termination**.
- `friends/tests.py`: Sending, accepting, declining, and unfriending requests.
- `groups_app/tests.py`: Group membership, role management, group post privacy.
- `pages_app/tests.py`: Page following, page post creation.
- `events_app/tests.py`: Event RSVP workflows.
- `marketplace/tests.py`: Product listings, category filters, seller inquiries.
- `api/tests.py`: DRF authentication, post serialization, token endpoints.

---

## 2. Executing the Test Suite

```powershell
# Run the entire test suite:
python manage.py test

# Run V4 core apps:
python manage.py test chat streaming social admin_dashboard
```

---

## 3. Verified Output

```text
Creating test database for alias 'default'...
....................................
----------------------------------------------------------------------
Ran 36 tests in 159.024s

OK
Destroying test database for alias 'default'...
Found 36 test(s).
System check identified no issues (0 silenced).
```

**100% Success Rate**: All 36 automated unit and integration tests pass with 0 errors and 0 failures.
