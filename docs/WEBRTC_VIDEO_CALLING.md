# CONNECTBOOK V4 — WEBRTC VIDEO & AUDIO CALLING

## Overview
ConnectBook V4 implements peer-to-peer 1-on-1 audio and video calling using the standard browser WebRTC API with Django Channels serving strictly as the out-of-band signaling mechanism.

---

## 1. Architectural Principles

1. **Signaling Only Over WebSockets**: The Django Channels WebSocket (`ws/call/<room_name>/`) transmits only lightweight signaling payloads (`offer`, `answer`, `ice-candidate`, `call-accept`, `call-end`).
2. **Zero Raw Media in Django**: Audio and video streams are encrypted and transmitted directly peer-to-peer between browsers via DTLS-SRTP, NEVER through the Django server or SQLite database.
3. **Strict Participant Authorization**: Only the designated `caller` and `receiver` for a `CallSession` can join the signaling room; third parties receive HTTP 403 Forbidden.

---

## 2. Signaling Lifecycle Flow

```
Alice (Caller)                      Django Channels                      Bob (Receiver)
     |                                    |                                    |
     |--- 1. GET /messages/call/start --->|                                    |
     |    (Create CallSession)            |--- 2. In-App Notification -------->|
     |                                    |                                    |
     |=== 3. Connect ws/call/<room>/ ====>|                                    |
     |                                    |<=== 4. Connect ws/call/<room>/ ====|
     |                                    |                                    |
     |--- 5. Offer (SDP) ---------------->|--- 5. Relay Offer ---------------->|
     |                                    |                                    |
     |<-- 6. Relay Answer <---------------|<-- 6. Answer (SDP) ----------------|
     |                                    |                                    |
     |<-> 7. ICE Candidates Exchange <--->|<-> 7. ICE Candidates Exchange <--->|
     |                                    |                                    |
     |================ 8. Peer-to-Peer Media (WebRTC Audio/Video) =============|
```

---

## 3. STUN and TURN Infrastructure

### Default STUN Configuration
Public Google STUN servers are configured in `call_room.html`:
```javascript
const rtcConfig = {
  iceServers: [
    { urls: 'stun:stun.l.google.com:19302' },
    { urls: 'stun:stun1.l.google.com:19302' }
  ]
};
```

### Production TURN Server Setup (Coturn)
In symmetric NAT or restrictive corporate firewall environments where direct P2P cannot establish, a TURN relay server is required.

To install Coturn on Ubuntu:
```bash
sudo apt-get install coturn
sudo nano /etc/turnserver.conf
```
Configuration settings:
```
listening-port=3478
tls-listening-port=5349
realm=connectbook.local
server-name=connectbook
lt-cred-mech
user=cbuser:StrongTurnSecretKey
```
Start service:
```bash
sudo systemctl enable coturn
sudo systemctl start coturn
```
Update `rtcConfig`:
```javascript
{
  urls: 'turn:turn.yourdomain.com:3478',
  username: 'cbuser',
  credential: 'StrongTurnSecretKey'
}
```

---

## 4. UI Controls in Call Room
- **Mute / Unmute Mic**: Dynamically sets `audioTrack.enabled`.
- **Camera On / Off**: Dynamically sets `videoTrack.enabled`.
- **Screen Share**: Acquires display via `navigator.mediaDevices.getDisplayMedia` and calls `sender.replaceTrack`.
- **Live Duration Timer**: Starts counting seconds automatically once peer connection state switches to `connected`.
- **Hang Up**: Broadcasts `call-end` signal, cleans up media tracks, records call duration, and redirects to inbox.
