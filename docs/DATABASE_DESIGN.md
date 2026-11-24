# CONNECTBOOK – DATABASE DESIGN

## 1. Database Engine
- **Engine:** SQLite 3 (`db.sqlite3`)
- **ORM:** Django 5.2 Object-Relational Mapper

## 2. Core Entities & Table Schema

### 1. `accounts_customuser`
- `id` (BigAutoField, PK)
- `username` (VARCHAR(150), UNIQUE)
- `email` (VARCHAR(254), UNIQUE)
- `password` (VARCHAR(128))
- `first_name` (VARCHAR(150))
- `last_name` (VARCHAR(150))
- `date_of_birth` (DATE, NULL)
- `gender` (VARCHAR(20))
- `is_verified` (BOOLEAN)
- `is_deactivated` (BOOLEAN)
- `created_at` (DATETIME)

### 2. `accounts_userprofile`
- `id` (BigAutoField, PK)
- `user_id` (ForeignKey -> CustomUser, OneToOne, CASCADE)
- `bio` (TEXT)
- `avatar` (VARCHAR(100), ImageField)
- `cover_photo` (VARCHAR(100), ImageField)
- `city` (VARCHAR(100))
- `hometown` (VARCHAR(100))
- `work` (VARCHAR(150))
- `education` (VARCHAR(150))
- `website` (VARCHAR(200))
- `relationship_status` (VARCHAR(50))
- `profile_visibility` (VARCHAR(20))

### 3. `friends_friendship`
- `id` (BigAutoField, PK)
- `user1_id` (ForeignKey -> CustomUser, CASCADE)
- `user2_id` (ForeignKey -> CustomUser, CASCADE)
- `created_at` (DATETIME)
- *Constraint:* `UNIQUE(user1_id, user2_id)` where `user1_id < user2_id` enforced in model `save()`.

### 4. `friends_friendrequest`
- `id` (BigAutoField, PK)
- `sender_id` (ForeignKey -> CustomUser, CASCADE)
- `receiver_id` (ForeignKey -> CustomUser, CASCADE)
- `status` (VARCHAR(20): pending, accepted, rejected, cancelled)
- `created_at` (DATETIME)
- `updated_at` (DATETIME)
- *Constraint:* `UNIQUE(sender_id, receiver_id)`

### 5. `social_post`
- `id` (BigAutoField, PK)
- `author_id` (ForeignKey -> CustomUser, CASCADE)
- `content` (TEXT)
- `privacy` (VARCHAR(20): public, friends, only_me)
- `group_id` (ForeignKey -> Group, NULL, CASCADE)
- `original_post_id` (ForeignKey -> Post, NULL, SET_NULL)
- `is_pinned` (BOOLEAN)
- `created_at` (DATETIME, INDEXED)

### 6. `social_reaction`
- `id` (BigAutoField, PK)
- `user_id` (ForeignKey -> CustomUser, CASCADE)
- `post_id` (ForeignKey -> Post, CASCADE)
- `reaction_type` (VARCHAR(20): like, love, haha, wow, sad, angry)
- *Constraint:* `UNIQUE(user_id, post_id)`

### 7. `social_comment`
- `id` (BigAutoField, PK)
- `post_id` (ForeignKey -> Post, CASCADE)
- `author_id` (ForeignKey -> CustomUser, CASCADE)
- `parent_id` (ForeignKey -> Comment, NULL, CASCADE)
- `content` (TEXT)
- `created_at` (DATETIME)

### 8. `stories_story`
- `id` (BigAutoField, PK)
- `author_id` (ForeignKey -> CustomUser, CASCADE)
- `media_type` (VARCHAR(10): image, video, text)
- `media_file` (FileField, NULL)
- `text_content` (TEXT)
- `background_color` (VARCHAR(50))
- `created_at` (DATETIME)
- `expires_at` (DATETIME)

### 9. `chat_conversation` & `chat_message`
- `chat_conversation`: `id`, `title`, `is_group`, `created_at`, `updated_at`
- `chat_conversationparticipant`: `conversation_id`, `user_id`, `is_admin`, `last_read_at`
- `chat_message`: `conversation_id`, `sender_id`, `content`, `attachment`, `is_read`, `created_at`

### 10. `notifications_notification`
- `id` (BigAutoField, PK)
- `recipient_id` (ForeignKey -> CustomUser, CASCADE)
- `actor_id` (ForeignKey -> CustomUser, CASCADE)
- `notification_type` (VARCHAR(30))
- `title` (VARCHAR(255))
- `message` (TEXT)
- `target_url` (VARCHAR(255))
- `is_read` (BOOLEAN)
- `created_at` (DATETIME)

### 11. `accounts_follow`
- `id` (BigAutoField, PK)
- `follower_id` (ForeignKey -> CustomUser, CASCADE)
- `followed_id` (ForeignKey -> CustomUser, CASCADE)
- `created_at` (DATETIME)
- *Constraint:* `UNIQUE(follower_id, followed_id)`

### 12. `accounts_userprivacysetting`
- `id` (BigAutoField, PK)
- `user_id` (OneToOneField -> CustomUser, CASCADE)
- `profile_visibility` (VARCHAR(20))
- `post_default_audience` (VARCHAR(20))
- `story_privacy` (VARCHAR(20))
- `friend_request_permission` (VARCHAR(30))
- `message_permission` (VARCHAR(20))
- `search_discoverability` (BOOLEAN)
- `read_receipts` (BOOLEAN)
- `online_status_visible` (BOOLEAN)
- `friends_list_visibility` (VARCHAR(20))
- `updated_at` (DATETIME)

### 13. `accounts_usersessionrecord`
- `id` (BigAutoField, PK)
- `user_id` (ForeignKey -> CustomUser, CASCADE)
- `session_key` (VARCHAR(40), INDEXED)
- `ip_address` (GenericIPAddressField, NULL)
- `user_agent` (VARCHAR(255))
- `device_type` (VARCHAR(50))
- `created_at` (DATETIME)
- `last_activity` (DATETIME)
- `is_active` (BOOLEAN)

### 14. `accounts_dataexportrequest` & `accounts_accountdeletionrequest`
- `DataExportRequest`: `id`, `user_id`, `requested_at`, `status`, `export_file`, `download_count`
- `AccountDeletionRequest`: `id`, `user_id`, `reason`, `status`, `requested_at`, `scheduled_deletion_date`

### 15. `pages_app_page` & `pages_app_pagefollow`
- `Page`: `id`, `name`, `slug` (UNIQUE), `category`, `bio`, `description`, `avatar`, `cover_photo`, `website`, `email`, `phone`, `address`, `owner_id`, `is_verified`, `created_at`, `updated_at`
- `PageFollow`: `page_id`, `user_id`, `created_at` (UNIQUE together)

### 16. `events_app_event` & `events_app_eventrsvp`
- `Event`: `id`, `title`, `description`, `organizer_id`, `cover_image`, `venue`, `start_time`, `end_time`, `privacy`, `created_at`, `updated_at`
- `EventRSVP`: `event_id`, `user_id`, `status` (going, interested, not_going), `created_at` (UNIQUE together)

### 17. `marketplace_marketplacelisting`
- `id` (BigAutoField, PK)
- `seller_id` (ForeignKey -> CustomUser, CASCADE)
- `title` (VARCHAR(200))
- `description` (TEXT)
- `price` (DECIMAL(10, 2))
- `category` (VARCHAR(50))
- `location` (VARCHAR(150))
- `image` (ImageField, NULL)
- `status` (VARCHAR(20): available, pending, sold)
- `created_at` (DATETIME)
- `updated_at` (DATETIME)

### 18. `streaming_livestream`
- `id` (BigAutoField, PK)
- `title` (VARCHAR(200))
- `description` (TEXT)
- `host_id` (ForeignKey -> CustomUser, CASCADE)
- `scheduled_start` (DATETIME)
- `actual_start` (DATETIME, NULL)
- `ended_at` (DATETIME, NULL)
- `status` (VARCHAR(20): scheduled, live, ended)
- `stream_key` (VARCHAR(64), UNIQUE)
- `thumbnail` (ImageField, NULL)
- `viewer_count` (PositiveIntegerField)
- `created_at` (DATETIME)

### 19. `admin_dashboard_sensitiveaccesslog`
- `id` (BigAutoField, PK)
- `staff_user_id` (ForeignKey -> CustomUser, CASCADE)
- `target_resource` (VARCHAR(150))
- `reason` (TEXT)
- `accessed_at` (DATETIME)
- `ip_address` (GenericIPAddressField, NULL)
- `approved_by_id` (ForeignKey -> CustomUser, NULL, SET_NULL)

