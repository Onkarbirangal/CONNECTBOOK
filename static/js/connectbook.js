/**
 * ConnectBook JavaScript Client
 * Handles real-time notifications, reactions, comments, story interactions,
 * desktop & mobile search suggestions, and theme toggling.
 */

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initSearch();
    initMobileSearch();
    initReactions();
    initComposerModal();
    initNotificationWebSocket();
    initKeyboardShortcuts();
    initPostViewRecorder();
    initLightboxKeyboard();
});

// ==========================================
// THEME HANDLING (Light / Dark)
// ==========================================
function initTheme() {
    const savedTheme = localStorage.getItem('cb-theme') || 'light';
    setTheme(savedTheme);

    const themeToggleBtn = document.getElementById('themeToggleBtn');
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', (e) => {
            e.preventDefault();
            const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            setTheme(newTheme);

            // Sync with backend if authenticated
            fetch('/accounts/api/toggle-theme/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken'),
                },
                body: JSON.stringify({ theme: newTheme })
            }).catch(() => {});
        });
    }
}

function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('cb-theme', theme);
    const themeIcon = document.getElementById('themeToggleIcon');
    if (themeIcon) {
        if (theme === 'dark') {
            themeIcon.className = 'bi bi-sun-fill text-warning';
        } else {
            themeIcon.className = 'bi bi-moon-stars-fill';
        }
    }
}

// ==========================================
// DESKTOP SEARCH AUTOCOMPLETE
// ==========================================
function initSearch() {
    const searchInput = document.getElementById('globalSearchInput');
    const searchDropdown = document.getElementById('globalSearchDropdown');

    if (!searchInput || !searchDropdown) return;

    let searchTimer = null;
    searchInput.addEventListener('input', () => {
        const query = searchInput.value.trim();
        clearTimeout(searchTimer);

        if (query.length < 2) {
            searchDropdown.style.display = 'none';
            searchDropdown.innerHTML = '';
            return;
        }

        searchTimer = setTimeout(() => {
            fetch(`/search/suggest/?q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(data => {
                    if (data.results && data.results.length > 0) {
                        let html = '';
                        data.results.forEach(item => {
                            html += `
                                <a href="${item.url}" class="cb-dropdown-item">
                                    <img src="${item.avatar}" class="cb-avatar cb-avatar-sm" alt="${item.title}">
                                    <div>
                                        <div class="fw-bold">${item.title}</div>
                                        <div class="small text-muted">${item.subtitle}</div>
                                    </div>
                                </a>
                            `;
                        });
                        html += `
                            <div class="p-2 border-top text-center">
                                <a href="/search/?q=${encodeURIComponent(query)}" class="small text-primary fw-bold">
                                    Search for "${query}"
                                </a>
                            </div>
                        `;
                        searchDropdown.innerHTML = html;
                        searchDropdown.style.display = 'block';
                    } else {
                        searchDropdown.innerHTML = `
                            <div class="p-3 text-center text-muted small">No results found for "${query}"</div>
                        `;
                        searchDropdown.style.display = 'block';
                    }
                })
                .catch(() => {
                    searchDropdown.style.display = 'none';
                });
        }, 250);
    });

    document.addEventListener('click', (e) => {
        if (!searchInput.contains(e.target) && !searchDropdown.contains(e.target)) {
            searchDropdown.style.display = 'none';
        }
    });
}

// ==========================================
// MOBILE SEARCH MODAL AUTOCOMPLETE
// ==========================================
function initMobileSearch() {
    const mobileInput = document.getElementById('mobileSearchInput');
    const mobileResults = document.getElementById('mobileSearchResults');

    if (!mobileInput || !mobileResults) return;

    let mobileTimer = null;
    mobileInput.addEventListener('input', () => {
        const query = mobileInput.value.trim();
        clearTimeout(mobileTimer);

        if (query.length < 2) {
            mobileResults.innerHTML = '<div class="p-4 text-center text-muted small">Type to search people, groups, and posts...</div>';
            return;
        }

        mobileTimer = setTimeout(() => {
            fetch(`/search/suggest/?q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(data => {
                    if (data.results && data.results.length > 0) {
                        let html = '<div class="list-group list-group-flush">';
                        data.results.forEach(item => {
                            html += `
                                <a href="${item.url}" class="list-group-item list-group-item-action d-flex align-items-center gap-3 py-3 border-bottom" style="background: transparent;">
                                    <img src="${item.avatar}" class="cb-avatar" alt="${item.title}">
                                    <div>
                                        <div class="fw-bold fs-6">${item.title}</div>
                                        <div class="small text-muted">${item.subtitle}</div>
                                    </div>
                                </a>
                            `;
                        });
                        html += `</div>
                            <div class="p-3 text-center">
                                <a href="/search/?q=${encodeURIComponent(query)}" class="btn btn-cb-primary w-100">
                                    See all results for "${query}"
                                </a>
                            </div>
                        `;
                        mobileResults.innerHTML = html;
                    } else {
                        mobileResults.innerHTML = `
                            <div class="p-4 text-center text-muted small">No matches found for "${query}"</div>
                        `;
                    }
                })
                .catch(() => {
                    mobileResults.innerHTML = '<div class="p-4 text-center text-muted small">Error performing search</div>';
                });
        }, 200);
    });
}

// ==========================================
// REACTIONS (Desktop Hover + Mobile Touch)
// ==========================================
function initReactions() {
    document.querySelectorAll('.cb-post-card').forEach(card => {
        bindPostCard(card);
    });
}

function bindPostCard(card) {
    const postId = card.dataset.postId;
    const likeBtn = card.querySelector('.cb-like-btn');
    const picker = card.querySelector('.cb-reaction-picker');

    if (!likeBtn || !picker) return;

    let hoverTimeout = null;
    let touchTimeout = null;

    // Desktop hover
    likeBtn.addEventListener('mouseenter', () => {
        hoverTimeout = setTimeout(() => {
            picker.style.display = 'flex';
        }, 250);
    });

    likeBtn.addEventListener('mouseleave', () => {
        clearTimeout(hoverTimeout);
    });

    picker.addEventListener('mouseleave', () => {
        picker.style.display = 'none';
    });

    // Mobile long-press / touch support
    likeBtn.addEventListener('touchstart', (e) => {
        touchTimeout = setTimeout(() => {
            picker.style.display = 'flex';
        }, 350);
    }, { passive: true });

    likeBtn.addEventListener('touchend', () => {
        clearTimeout(touchTimeout);
    });

    // Click on like button toggles standard Like
    likeBtn.addEventListener('click', (e) => {
        e.preventDefault();
        const currentActive = likeBtn.dataset.currentReaction;
        const targetReaction = currentActive ? 'none' : 'like';
        submitReaction(postId, targetReaction, card);
        picker.style.display = 'none';
    });

    // Reaction picker items click
    picker.querySelectorAll('.cb-reaction-item').forEach(item => {
        const handleReactionSelect = (e) => {
            e.stopPropagation();
            e.preventDefault();
            const rType = item.dataset.reaction;
            submitReaction(postId, rType, card);
            picker.style.display = 'none';
        };
        item.addEventListener('click', handleReactionSelect);
        item.addEventListener('touchend', handleReactionSelect);
    });
}

function submitReaction(postId, reactionType, card) {
    fetch(`/posts/${postId}/react/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken'),
        },
        body: JSON.stringify({ reaction_type: reactionType })
    })
    .then(res => res.json())
    .then(data => {
        if (data.status === 'success') {
            updatePostReactionUI(card, data);
        }
    })
    .catch(err => console.error('Reaction error:', err));
}

function updatePostReactionUI(card, data) {
    const likeBtn = card.querySelector('.cb-like-btn');
    const statsContainer = card.querySelector('.cb-reaction-count-text');

    if (statsContainer) {
        if (data.total_reactions > 0) {
            statsContainer.innerHTML = `<span class="badge bg-primary rounded-pill"><i class="bi bi-hand-thumbs-up-fill"></i> ${data.total_reactions}</span>`;
        } else {
            statsContainer.innerHTML = '';
        }
    }

    // Reset reaction classes
    likeBtn.className = 'cb-post-action-btn cb-like-btn';
    likeBtn.dataset.currentReaction = data.user_reaction || '';

    const textSpan = likeBtn.querySelector('.cb-action-label');
    const iconSpan = likeBtn.querySelector('.cb-action-icon');

    if (data.user_reaction) {
        likeBtn.classList.add(`active-${data.user_reaction}`);
        const emojis = {
            like: '👍 Like',
            love: '❤️ Love',
            care: '🥰 Care',
            haha: '😆 Haha',
            wow: '😮 Wow',
            sad: '😢 Sad',
            angry: '😡 Angry'
        };
        if (textSpan) textSpan.textContent = emojis[data.user_reaction] || 'Like';
        if (iconSpan) iconSpan.style.display = 'none';
    } else {
        if (textSpan) textSpan.textContent = 'Like';
        if (iconSpan) iconSpan.style.display = 'inline-block';
    }
}

// ==========================================
// POST COMPOSER MODAL & PREVIEWS
// ==========================================
function initComposerModal() {
    const mediaInput = document.getElementById('postMediaInput');
    const previewContainer = document.getElementById('postMediaPreviewContainer');

    if (mediaInput && previewContainer) {
        mediaInput.addEventListener('change', () => {
            previewContainer.innerHTML = '';
            if (mediaInput.files && mediaInput.files.length > 0) {
                Array.from(mediaInput.files).forEach((file, index) => {
                    const reader = new FileReader();
                    reader.onload = (e) => {
                        const isVideo = file.type.startsWith('video');
                        const itemDiv = document.createElement('div');
                        itemDiv.className = 'position-relative d-inline-block m-1';
                        itemDiv.style.width = '75px';
                        itemDiv.style.height = '75px';

                        if (isVideo) {
                            itemDiv.innerHTML = `
                                <video src="${e.target.result}" style="width:100%; height:100%; object-fit:cover; border-radius:6px;"></video>
                                <span class="badge bg-dark position-absolute bottom-0 start-0 m-1" style="font-size: 9px;">Video</span>
                            `;
                        } else {
                            itemDiv.innerHTML = `
                                <img src="${e.target.result}" style="width:100%; height:100%; object-fit:cover; border-radius:6px;" alt="preview">
                            `;
                        }
                        previewContainer.appendChild(itemDiv);
                    };
                    reader.readAsDataURL(file);
                });
                previewContainer.style.display = 'flex';
            } else {
                previewContainer.style.display = 'none';
            }
        });
    }
}

// ==========================================
// REAL-TIME NOTIFICATIONS WEBSOCKET
// ==========================================
function initNotificationWebSocket() {
    const wsScheme = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsScheme}//${window.location.host}/ws/notifications/`;

    try {
        const socket = new WebSocket(wsUrl);

        socket.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.type === 'notification') {
                showToastNotification(data);
                updateNotificationBadge(data.unread_count);
            }
        };

        socket.onerror = () => {
            // Graceful fallback to periodic check every 30s
            setInterval(checkNotificationsFallback, 30000);
        };
    } catch {
        setInterval(checkNotificationsFallback, 30000);
    }
}

function updateNotificationBadge(count) {
    document.querySelectorAll('.cb-badge').forEach(badge => {
        if (badge.id === 'notificationBadge' || badge.closest('.cb-bottom-tab')) {
            if (count > 0) {
                badge.textContent = count > 99 ? '99+' : count;
                badge.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
            }
        }
    });
}

function showToastNotification(notif) {
    const container = document.getElementById('toastNotificationContainer');
    if (!container) return;

    const toastDiv = document.createElement('div');
    toastDiv.className = 'toast show align-items-center border-0 shadow-lg mb-2';
    toastDiv.style.background = 'var(--cb-card)';
    toastDiv.style.color = 'var(--cb-text)';
    toastDiv.setAttribute('role', 'alert');
    toastDiv.innerHTML = `
        <div class="d-flex p-2">
            <img src="${notif.actor_avatar || '/static/images/default-avatar.svg'}" class="cb-avatar cb-avatar-sm me-2" alt="">
            <div class="toast-body p-0 flex-grow-1">
                <div class="fw-bold small">${escapeHtml(notif.title)}</div>
                <div class="text-muted small">${escapeHtml(notif.message)}</div>
            </div>
            <button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    container.appendChild(toastDiv);

    setTimeout(() => {
        toastDiv.remove();
    }, 6000);
}

function checkNotificationsFallback() {
    fetch('/notifications/api/unread-count/')
        .then(res => res.json())
        .then(data => {
            updateNotificationBadge(data.unread_count);
        })
        .catch(() => {});
}

// ==========================================
// UTILITY FUNCTIONS
// ==========================================
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

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ==========================================
// KEYBOARD SHORTCUTS & TOAST HELPERS
// ==========================================
function initKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        const tag = (e.target.tagName || '').toUpperCase();
        const isInput = tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || e.target.isContentEditable;

        // "/" key focuses global search input
        if (e.key === '/' && !isInput && !e.ctrlKey && !e.metaKey && !e.altKey) {
            e.preventDefault();
            const desktopInput = document.getElementById('globalSearchInput');
            if (desktopInput && window.innerWidth >= 768) {
                desktopInput.focus();
                desktopInput.select();
            } else {
                const mobileModal = document.getElementById('mobileSearchModal');
                if (mobileModal) {
                    const bsModal = bootstrap.Modal.getOrCreateInstance(mobileModal);
                    bsModal.show();
                    setTimeout(() => {
                        const mInput = document.getElementById('mobileSearchInput');
                        if (mInput) mInput.focus();
                    }, 300);
                }
            }
        }

        // "Escape" key dismisses search dropdown, clears focus
        if (e.key === 'Escape') {
            const dropdown = document.getElementById('globalSearchDropdown');
            if (dropdown) dropdown.style.display = 'none';
        }
    });
}

window.showToast = function(message, type = 'primary') {
    const container = document.getElementById('toastNotificationContainer');
    if (!container) return;
    const toastDiv = document.createElement('div');
    toastDiv.className = `alert alert-${type} alert-dismissible fade show shadow-sm`;
    toastDiv.innerHTML = `
        <i class="bi bi-info-circle me-1"></i> ${escapeHtml(message)}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    container.appendChild(toastDiv);
    setTimeout(() => {
        toastDiv.remove();
    }, 5000);
};

window.votePoll = function(postId, optionId) {
    const formData = new FormData();
    formData.append('option_id', optionId);

    fetch(`/posts/${postId}/poll/vote/`, {
        method: 'POST',
        headers: {
            'X-CSRFToken': getCookie('csrftoken'),
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: formData
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'ok') {
            const container = document.getElementById(`poll-options-${postId}`);
            const counter = document.getElementById(`poll-votes-count-${postId}`);
            if (counter) counter.textContent = `${data.total_votes} vote${data.total_votes === 1 ? '' : 's'}`;
            if (container && data.options) {
                container.innerHTML = data.options.map(opt => `
                    <div class="position-relative p-2 rounded border option-card" style="cursor: pointer; overflow: hidden; background: var(--cb-card);" onclick="votePoll(${postId}, ${opt.id})">
                        <div class="position-absolute top-0 start-0 h-100 bg-primary bg-opacity-10" style="width: ${opt.percentage}%; transition: width 0.4s ease; z-index: 1;"></div>
                        <div class="position-relative d-flex justify-content-between align-items-center" style="z-index: 2;">
                            <span class="fw-semibold small">${opt.text}</span>
                            <span class="badge bg-primary-subtle text-primary fw-bold" style="font-size: 11px;">${opt.percentage}% (${opt.votes})</span>
                        </div>
                    </div>
                `).join('');
            }
        }
    })
    .catch(err => console.error("Poll voting error:", err));
};

// ==========================================
// CONNECTBOOK V5 LIGHTBOX GALLERY
// ==========================================
window.lightboxState = {
    postId: null,
    images: [],
    currentIndex: 0
};

window.openLightbox = function(postId, imageIndex = 0) {
    const postGrid = document.querySelector(`.cb-post-media-grid[data-post-id="${postId}"]`);
    if (!postGrid) return;

    const imgElements = postGrid.querySelectorAll('img.cb-post-media-item');
    if (!imgElements || imgElements.length === 0) return;

    window.lightboxState.postId = postId;
    window.lightboxState.images = Array.from(imgElements).map(img => ({
        src: img.dataset.src || img.src,
        caption: img.dataset.caption || '',
        alt: img.alt || ''
    }));
    window.lightboxState.currentIndex = Math.max(0, Math.min(imageIndex, window.lightboxState.images.length - 1));

    const modal = document.getElementById('cbLightboxModal');
    if (modal) {
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
        renderLightboxCurrent();
    }
};

window.closeLightbox = function() {
    const modal = document.getElementById('cbLightboxModal');
    if (modal) {
        modal.style.display = 'none';
        document.body.style.overflow = '';
    }
};

window.prevLightboxImage = function() {
    if (window.lightboxState.images.length <= 1) return;
    window.lightboxState.currentIndex = (window.lightboxState.currentIndex - 1 + window.lightboxState.images.length) % window.lightboxState.images.length;
    renderLightboxCurrent();
};

window.nextLightboxImage = function() {
    if (window.lightboxState.images.length <= 1) return;
    window.lightboxState.currentIndex = (window.lightboxState.currentIndex + 1) % window.lightboxState.images.length;
    renderLightboxCurrent();
};

function renderLightboxCurrent() {
    const { images, currentIndex } = window.lightboxState;
    if (!images || images.length === 0) return;

    const current = images[currentIndex];
    const imgEl = document.getElementById('cbLightboxImage');
    const counterEl = document.getElementById('cbLightboxCounter');
    const captionEl = document.getElementById('cbLightboxCaption');
    const downloadEl = document.getElementById('cbLightboxDownloadBtn');
    const prevBtn = document.getElementById('cbLightboxPrevBtn');
    const nextBtn = document.getElementById('cbLightboxNextBtn');

    if (imgEl) {
        imgEl.style.opacity = '0.3';
        imgEl.src = current.src;
        imgEl.onload = () => { imgEl.style.opacity = '1'; };
    }
    if (counterEl) counterEl.textContent = `${currentIndex + 1} / ${images.length}`;
    if (downloadEl) downloadEl.href = current.src;

    if (captionEl) {
        if (current.caption && current.caption.trim()) {
            captionEl.textContent = current.caption;
            captionEl.style.display = 'block';
        } else {
            captionEl.style.display = 'none';
        }
    }

    if (prevBtn) prevBtn.style.display = images.length > 1 ? 'block' : 'none';
    if (nextBtn) nextBtn.style.display = images.length > 1 ? 'block' : 'none';
}

function initLightboxKeyboard() {
    document.addEventListener('keydown', (e) => {
        const modal = document.getElementById('cbLightboxModal');
        if (!modal || modal.style.display === 'none') return;

        if (e.key === 'Escape') {
            closeLightbox();
        } else if (e.key === 'ArrowLeft') {
            prevLightboxImage();
        } else if (e.key === 'ArrowRight') {
            nextLightboxImage();
        }
    });
}

// ==========================================
// CONNECTBOOK V5 POST PERFORMANCE & INSIGHTS
// ==========================================
window.openPostInsights = function(postId) {
    const modalEl = document.getElementById('cbPostInsightsModal');
    if (!modalEl) return;

    const bsModal = bootstrap.Modal.getOrCreateInstance(modalEl);
    bsModal.show();

    const spinner = document.getElementById('cbPostInsightsSpinner');
    const dataContainer = document.getElementById('cbPostInsightsData');
    if (spinner) spinner.style.display = 'block';
    if (dataContainer) dataContainer.style.display = 'none';

    fetch(`/posts/${postId}/insights/`, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    })
    .then(r => r.json())
    .then(res => {
        if (res.status === 'ok') {
            const data = res.data;
            if (spinner) spinner.style.display = 'none';
            if (dataContainer) dataContainer.style.display = 'block';

            document.getElementById('insightReach').textContent = data.reach || 0;
            document.getElementById('insightImpressions').textContent = data.impressions || 0;
            document.getElementById('insightEngagementRate').textContent = `${data.engagement_rate || 0}%`;
            document.getElementById('insightTotalReactions').textContent = data.reactions_count || 0;
            document.getElementById('insightComments').textContent = data.comments_count || 0;
            document.getElementById('insightShares').textContent = data.shares_count || 0;

            const breakdown = data.reactions_breakdown || {};
            document.getElementById('reactionCountLike').textContent = breakdown.like || 0;
            document.getElementById('reactionCountLove').textContent = breakdown.love || 0;
            document.getElementById('reactionCountCare').textContent = breakdown.care || 0;
            document.getElementById('reactionCountHaha').textContent = breakdown.haha || 0;
            document.getElementById('reactionCountWow').textContent = breakdown.wow || 0;
            document.getElementById('reactionCountSad').textContent = breakdown.sad || 0;
            document.getElementById('reactionCountAngry').textContent = breakdown.angry || 0;
        } else {
            showToast(res.message || 'Unable to load post insights.', 'warning');
            bsModal.hide();
        }
    })
    .catch(err => {
        console.error("Insights fetch error:", err);
        showToast('Error loading insights.', 'danger');
        bsModal.hide();
    });
};

// ==========================================
// CONNECTBOOK V5 COPY POST LINK HELPER
// ==========================================
window.copyPostLink = function(url) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(url)
            .then(() => showToast('Post link copied to clipboard!', 'success'))
            .catch(() => fallbackCopy(url));
    } else {
        fallbackCopy(url);
    }
};

function fallbackCopy(text) {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'fixed';
    textArea.style.opacity = '0';
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    try {
        document.execCommand('copy');
        showToast('Post link copied to clipboard!', 'success');
    } catch {
        showToast('Failed to copy post link.', 'warning');
    }
    document.body.removeChild(textArea);
}

// ==========================================
// CONNECTBOOK V5 AUTOMATIC VIEW TRACKER
// ==========================================
function initPostViewRecorder() {
    if (!('IntersectionObserver' in window)) return;

    const recordedPosts = new Set();
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const postId = entry.target.dataset.postId;
                if (postId && !recordedPosts.has(postId)) {
                    recordedPosts.add(postId);
                    fetch(`/posts/${postId}/record-view/`, {
                        method: 'POST',
                        headers: {
                            'X-CSRFToken': getCookie('csrftoken'),
                            'X-Requested-With': 'XMLHttpRequest'
                        }
                    }).catch(() => {});
                }
            }
        });
    }, { threshold: 0.5 });

    document.querySelectorAll('.cb-post-card').forEach(card => {
        observer.observe(card);
    });
}


