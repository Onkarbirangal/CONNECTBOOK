/**
 * ConnectBook Stories Carousel and Full-Screen Viewer
 */

class StoryViewer {
    constructor() {
        this.modal = document.getElementById('storyViewerModal');
        this.progressBarContainer = document.getElementById('storyProgressBarContainer');
        this.contentContainer = document.getElementById('storyViewerMedia');
        this.authorNameElem = document.getElementById('storyViewerAuthorName');
        this.authorAvatarElem = document.getElementById('storyViewerAuthorAvatar');
        this.timeElem = document.getElementById('storyViewerTime');
        this.prevBtn = document.getElementById('storyViewerPrevBtn');
        this.nextBtn = document.getElementById('storyViewerNextBtn');
        this.closeBtn = document.getElementById('storyViewerCloseBtn');

        this.currentStories = [];
        this.currentIndex = 0;
        this.timer = null;
        this.duration = 5000; // 5 seconds per story

        this.init();
    }

    init() {
        if (!this.modal) return;

        if (this.closeBtn) {
            this.closeBtn.addEventListener('click', () => this.close());
        }

        if (this.prevBtn) {
            this.prevBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.prev();
            });
        }

        if (this.nextBtn) {
            this.nextBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.next();
            });
        }

        document.querySelectorAll('.cb-story-card:not(.cb-create-story-card)').forEach(card => {
            card.addEventListener('click', () => {
                const authorId = card.dataset.authorId;
                this.loadStories(authorId);
            });
        });
    }

    loadStories(authorId) {
        fetch(`/stories/api/user/${authorId}/`)
            .then(res => res.json())
            .then(data => {
                if (data.stories && data.stories.length > 0) {
                    this.currentStories = data.stories;
                    this.currentIndex = 0;
                    this.open();
                }
            })
            .catch(err => console.error('Error fetching stories:', err));
    }

    open() {
        this.modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
        this.renderStory();
    }

    close() {
        this.modal.style.display = 'none';
        document.body.style.overflow = '';
        clearTimeout(this.timer);
    }

    renderStory() {
        clearTimeout(this.timer);
        if (this.currentIndex >= this.currentStories.length) {
            this.close();
            return;
        }

        const story = this.currentStories[this.currentIndex];

        // Mark as viewed on backend
        fetch(`/stories/${story.id}/view/`, {
            method: 'POST',
            headers: { 'X-CSRFToken': getCookie('csrftoken') }
        }).catch(() => {});

        // Setup progress bars
        this.progressBarContainer.innerHTML = '';
        this.currentStories.forEach((_, idx) => {
            const seg = document.createElement('div');
            seg.className = 'cb-story-progress-segment';
            const fill = document.createElement('div');
            fill.className = 'cb-story-progress-fill';
            if (idx < this.currentIndex) {
                fill.style.width = '100%';
            } else if (idx === this.currentIndex) {
                fill.style.width = '0%';
                setTimeout(() => { fill.style.transition = `width ${this.duration}ms linear`; fill.style.width = '100%'; }, 50);
            } else {
                fill.style.width = '0%';
            }
            seg.appendChild(fill);
            this.progressBarContainer.appendChild(seg);
        });

        // Set author info
        this.authorNameElem.textContent = story.author_name;
        this.authorAvatarElem.src = story.author_avatar;
        this.timeElem.textContent = story.time_ago;

        // Render content
        if (story.media_type === 'image') {
            this.contentContainer.innerHTML = `
                <img src="${story.media_url}" style="width:100%; height:100%; object-fit:contain;" alt="">
            `;
        } else if (story.media_type === 'video') {
            this.contentContainer.innerHTML = `
                <video src="${story.media_url}" autoplay playsinline style="width:100%; height:100%; object-fit:contain;"></video>
            `;
        } else {
            // Text story
            this.contentContainer.innerHTML = `
                <div style="background: ${story.background_color}; width:100%; height:100%; display:flex; align-items:center; justify-content:center; padding:30px; color:#fff; font-size:24px; font-weight:bold; text-align:center;">
                    ${escapeHtml(story.text_content)}
                </div>
            `;
        }

        this.timer = setTimeout(() => {
            this.next();
        }, this.duration);
    }

    next() {
        if (this.currentIndex < this.currentStories.length - 1) {
            this.currentIndex++;
            this.renderStory();
        } else {
            this.close();
        }
    }

    prev() {
        if (this.currentIndex > 0) {
            this.currentIndex--;
            this.renderStory();
        }
    }
}

let activeStoryViewerInstance = null;

document.addEventListener('DOMContentLoaded', () => {
    activeStoryViewerInstance = new StoryViewer();

    const replyBtn = document.getElementById('storyReplySendBtn');
    const replyInput = document.getElementById('storyReplyInput');
    if (replyBtn && replyInput) {
        const sendReply = () => {
            const text = replyInput.value.trim();
            if (!text || !activeStoryViewerInstance || !activeStoryViewerInstance.currentStories) return;
            const current = activeStoryViewerInstance.currentStories[activeStoryViewerInstance.currentIndex];
            if (!current) return;

            const fd = new FormData();
            fd.append('message', text);

            fetch(`/stories/${current.id}/reply/`, {
                method: 'POST',
                headers: { 'X-CSRFToken': getCookie('csrftoken') },
                body: fd
            })
            .then(r => r.json())
            .then(data => {
                replyInput.value = '';
                if (window.showToast) window.showToast('Reply sent to story author!', 'success');
            })
            .catch(() => {});
        };

        replyBtn.addEventListener('click', sendReply);
        replyInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                sendReply();
            }
        });
    }
});

window.submitStoryReaction = function(emoji) {
    if (!activeStoryViewerInstance || !activeStoryViewerInstance.currentStories) return;
    const current = activeStoryViewerInstance.currentStories[activeStoryViewerInstance.currentIndex];
    if (!current) return;

    const fd = new FormData();
    fd.append('reaction_type', emoji);

    fetch(`/stories/${current.id}/react/`, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
        body: fd
    })
    .then(r => r.json())
    .then(() => {
        if (window.showToast) window.showToast(`Reacted ${emoji}`, 'primary');
    })
    .catch(() => {});
};

window.viewHighlight = function(highlightId) {
    if (!activeStoryViewerInstance) activeStoryViewerInstance = new StoryViewer();
    fetch(`/stories/api/highlight/${highlightId}/`)
        .then(r => r.json())
        .then(data => {
            if (data.stories && data.stories.length > 0) {
                activeStoryViewerInstance.currentStories = data.stories;
                activeStoryViewerInstance.currentIndex = 0;
                activeStoryViewerInstance.open();
            }
        })
        .catch(err => console.error("Error loading highlight:", err));
};
