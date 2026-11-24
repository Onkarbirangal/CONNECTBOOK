/**
 * ConnectBook Real-Time Messenger Client
 */

class ConnectBookChat {
    constructor(conversationId, currentUserId) {
        this.conversationId = conversationId;
        this.currentUserId = currentUserId;
        this.socket = null;
        this.replyToId = null;
        this.messagesContainer = document.getElementById('chatMessagesContainer');
        this.messageInput = document.getElementById('chatMessageInput');
        this.sendBtn = document.getElementById('chatSendBtn');
        this.typingIndicator = document.getElementById('chatTypingIndicator');
        this.replyPreview = document.getElementById('chatReplyPreview');
        this.replyAuthor = document.getElementById('chatReplyAuthor');
        this.replyText = document.getElementById('chatReplyText');
        this.typingTimeout = null;

        window.chatInstance = this;
        this.init();
    }

    setReplyTo(msgId, authorName, text) {
        this.replyToId = msgId;
        if (this.replyPreview && this.replyAuthor && this.replyText) {
            this.replyAuthor.textContent = authorName;
            this.replyText.textContent = text;
            this.replyPreview.style.setProperty('display', 'flex', 'important');
        }
        if (this.messageInput) this.messageInput.focus();
    }

    clearReplyTo() {
        this.replyToId = null;
        if (this.replyPreview) {
            this.replyPreview.style.setProperty('display', 'none', 'important');
        }
    }

    init() {
        this.scrollToBottom();
        this.connectWebSocket();
        this.bindEvents();

        if (window.visualViewport) {
            window.visualViewport.addEventListener('resize', () => {
                this.scrollToBottom();
            });
        }
    }

    connectWebSocket() {
        const wsScheme = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${wsScheme}//${window.location.host}/ws/chat/${this.conversationId}/`;

        this.socket = new WebSocket(wsUrl);

        this.socket.onopen = () => {
            console.log('Connected to chat socket');
        };

        this.socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'message') {
                this.appendMessage(data);
            } else if (data.type === 'typing') {
                this.showTyping(data);
            } else if (data.type === 'delete') {
                const el = document.getElementById(`msg-${data.message_id}`);
                if (el) el.innerHTML = '<div class="fst-italic opacity-50 small">This message was deleted</div>';
            } else if (data.type === 'edit') {
                const el = document.getElementById(`msg-${data.message_id}`);
                if (el) {
                    const textDiv = el.querySelector('div');
                    if (textDiv) textDiv.textContent = data.content;
                }
            }
        };

        this.socket.onerror = (err) => {
            console.warn('WebSocket error, falling back to HTTP polling:', err);
            this.startHttpPolling();
        };

        this.socket.onclose = () => {
            console.log('Chat socket closed');
        };
    }

    bindEvents() {
        if (this.sendBtn) {
            this.sendBtn.addEventListener('click', () => this.sendMessage());
        }

        if (this.messageInput) {
            this.messageInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                } else {
                    this.notifyTyping();
                }
            });
        }
    }

    notifyTyping() {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({ action: 'typing', is_typing: true }));
            clearTimeout(this.typingTimeout);
            this.typingTimeout = setTimeout(() => {
                if (this.socket && this.socket.readyState === WebSocket.OPEN) {
                    this.socket.send(JSON.stringify({ action: 'typing', is_typing: false }));
                }
            }, 1500);
        }
    }

    showTyping(data) {
        if (!this.typingIndicator) return;
        if (data.is_typing) {
            this.typingIndicator.textContent = `${data.sender_name} is typing...`;
            this.typingIndicator.style.display = 'block';
        } else {
            this.typingIndicator.style.display = 'none';
        }
    }

    handleAttachment(fileInput) {
        if (!fileInput || !fileInput.files || !fileInput.files[0]) return;
        const file = fileInput.files[0];
        const formData = new FormData();
        formData.append('attachment', file);
        if (this.replyToId) {
            formData.append('reply_to_id', this.replyToId);
            this.clearReplyTo();
        }

        fetch(`/chat/${this.conversationId}/send/`, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken') || '',
            },
            body: formData
        })
        .then(res => res.json())
        .then(data => {
            if (data.status === 'success') {
                this.appendMessage(data.message);
                fileInput.value = '';
            }
        })
        .catch(err => {
            console.error('Failed to upload attachment:', err);
        });
    }

    sendMessage() {
        const text = this.messageInput.value.trim();
        if (!text) return;

        const replyId = this.replyToId;
        this.clearReplyTo();

        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            this.socket.send(JSON.stringify({
                action: 'message',
                message: text,
                reply_to_id: replyId
            }));
            this.messageInput.value = '';
        } else {
            // HTTP Fallback
            fetch(`/chat/${this.conversationId}/send/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken') || '',
                },
                body: JSON.stringify({ message: text, reply_to_id: replyId })
            })
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success') {
                    this.appendMessage(data.message);
                    this.messageInput.value = '';
                }
            });
        }
    }

    appendMessage(data) {
        if (!this.messagesContainer) return;

        const isMe = data.sender_id === this.currentUserId;
        const isNearBottom = this.messagesContainer.scrollHeight - this.messagesContainer.scrollTop - this.messagesContainer.clientHeight < 160;

        const rowDiv = document.createElement('div');
        rowDiv.id = `msg-row-${data.message_id || data.id}`;
        rowDiv.className = `d-flex ${isMe ? 'justify-content-end' : 'align-items-end gap-2'} mb-2 cb-msg-row ${isMe ? 'cb-msg-row-sent' : 'cb-msg-row-received'}`;

        let avatarHtml = '';
        if (!isMe) {
            const avatarUrl = data.sender_avatar || '/static/images/default-avatar.svg';
            avatarHtml = `<img src="${avatarUrl}" class="cb-avatar cb-avatar-sm shadow-sm flex-shrink-0" style="width: 30px; height: 30px; margin-bottom: 2px;" alt="" onerror="this.src='/static/images/default-avatar.svg'">`;
        }

        let replyHtml = '';
        if (data.reply_to) {
            replyHtml = `
                <div class="p-1 px-2 mb-1 rounded bg-black bg-opacity-10 border-start border-3 ${isMe ? 'border-light' : 'border-primary'} text-truncate" style="font-size: 11px;">
                    <strong>${escapeHtml(data.reply_to.sender_name)}</strong>: ${escapeHtml(data.reply_to.content)}
                </div>
            `;
        }

        let attachmentHtml = '';
        if (data.attachment_url) {
            attachmentHtml = `
                <div class="mb-2">
                    <img src="${data.attachment_url}" class="img-fluid rounded shadow-sm" style="max-height: 220px; object-fit: cover; cursor: pointer;" onclick="window.open(this.src)" alt="Attachment">
                </div>
            `;
        }

        rowDiv.innerHTML = `
            ${avatarHtml}
            <div class="cb-msg-bubble ${isMe ? 'cb-msg-sent' : 'cb-msg-received'}" id="msg-${data.message_id || data.id}">
                ${replyHtml}
                ${attachmentHtml}
                <div>${escapeHtml(data.content)}</div>
                <div class="d-flex align-items-center ${isMe ? 'justify-content-end' : 'justify-content-between'} gap-2 mt-1 opacity-75" style="font-size: 10px;">
                    <span>${data.created_at}</span>
                    ${isMe ? '<i class="bi bi-check2-all text-white"></i>' : ''}
                </div>
            </div>
        `;

        this.messagesContainer.appendChild(rowDiv);

        if (isMe || isNearBottom) {
            this.scrollToBottom();
        }
    }

    scrollToBottom() {
        if (this.messagesContainer) {
            this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
        }
    }

    startHttpPolling() {
        setInterval(() => {
            fetch(`/chat/${this.conversationId}/messages/`)
                .then(res => res.json())
                .then(data => {
                    // Refresh new messages if any
                })
                .catch(() => {});
        }, 4000);
    }
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}
