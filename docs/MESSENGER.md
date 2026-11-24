# CONNECTBOOK V4 — MESSENGER & REAL-TIME COMMUNICATION

## Overview
The ConnectBook Messenger is a Facebook-inspired chat application supporting direct 1-on-1 messaging, message replies, message reactions, editing, soft deletion, conversation mute/archive, and WebRTC audio and video calling.

---

## 1. Features & Capabilities

1. **Real-Time WebSocket Transport**: Powered by `ChatConsumer` on `ws/chat/<conversation_id>/`.
2. **Instant Audio & Video Calling**: Header buttons allow users to initiate high-definition video calls or audio calls directly with the active recipient.
3. **Message Replies**: Quoted reply bubbles linking to referenced parent messages.
4. **Message Reactions**: Interactive emojis (`like`, `love`, `haha`, `wow`, `sad`, `angry`).
5. **Edit & Soft Delete**: Senders can edit existing messages (flagged with `edited` timestamp) or delete messages (rendered as "This message was deleted").
6. **Mute & Archive**: Mute notifications for active chats or move conversations to the archived tab.
7. **Typing Indicators**: Real-time "Typing..." status broadcasted over WebSocket.

---

## 2. API & Routing

- `GET /messages/`: Inbox view with conversation list and active chat.
- `GET /messages/<conversation_id>/`: Open specific conversation.
- `GET /messages/direct/<user_id>/`: Find or create a direct conversation with a user.
- `POST /messages/<conversation_id>/send/`: HTTP fallback for sending text and media attachments.
- `GET /messages/call/start/<user_id>/<call_type>/`: Start a video or audio call session.
- `GET /messages/call/<room_name>/`: WebRTC peer-to-peer call room.
- `POST /messages/call/<room_name>/end/`: Terminate call session and log duration.
