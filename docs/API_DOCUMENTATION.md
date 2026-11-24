# CONNECTBOOK – REST API DOCUMENTATION

Base URL: `/api/`  
Authentication: Session Authentication / Bearer Token  
Default Pagination: 10 items per page

---

### 1. Current User Profile
- **Endpoint:** `GET /api/me/`
- **Description:** Returns the authenticated user's profile and summary details.
- **Response `200 OK`:**
```json
{
  "id": 1,
  "username": "admin",
  "first_name": "Admin",
  "last_name": "User",
  "display_name": "Admin User",
  "profile": {
    "bio": "System Administrator & Lead Architect of ConnectBook.",
    "city": "San Francisco, CA",
    "work": "ConnectBook Inc.",
    "education": "Stanford University",
    "website": "",
    "avatar_url": "/static/images/default-avatar.svg",
    "cover_url": "/static/images/default-cover.svg"
  }
}
```

---

### 2. Posts Endpoints
- **List Public Posts:** `GET /api/posts/`
- **Create Post:** `POST /api/posts/`
  - Body:
  ```json
  {
    "content": "Hello ConnectBook API!",
    "privacy": "public"
  }
  ```
- **Post Detail / Update / Delete:** `GET / PUT / DELETE /api/posts/<id>/`

---

### 3. Comments Endpoints
- **List Post Comments:** `GET /api/posts/<post_id>/comments/`
- **Add Comment:** `POST /api/posts/<post_id>/comments/`
  - Body:
  ```json
  {
    "content": "Awesome post!"
  }
  ```

---

### 4. Stories Endpoint
- **Active Stories:** `GET /api/stories/`
  - Returns non-expired stories active within the last 24 hours.

---

### 5. Chat Messages Endpoint
- **Conversation Messages:** `GET /api/conversations/<conversation_id>/messages/`
- **Send Message:** `POST /api/conversations/<conversation_id>/messages/`
  - Body:
  ```json
  {
    "content": "Hey there!"
  }
  ```

---

### 6. Groups Endpoint
- **List & Create Groups:** `GET / POST /api/groups/`

---

### 7. Notifications Endpoint
- **User Notifications:** `GET /api/notifications/`
