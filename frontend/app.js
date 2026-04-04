/* ═══════════════════════════════════════════════════════════════
   NexusAI — Frontend Application Logic
   Connects to FastAPI backend at /api/auth/* and /api/chat/*
   ═══════════════════════════════════════════════════════════════ */

const API_BASE = 'http://localhost:8000';

// ── State ────────────────────────────────────────────────────────
const state = {
    token: localStorage.getItem('nexus_token') || null,
    user: JSON.parse(localStorage.getItem('nexus_user') || 'null'),
    currentSessionId: null,
    sessions: [],
    isLoading: false,
};

// ── DOM References ──────────────────────────────────────────────
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

const authPage      = $('#auth-page');
const chatPage      = $('#chat-page');
const loginForm     = $('#login-form');
const signupForm    = $('#signup-form');
const tabLogin      = $('#tab-login');
const tabSignup     = $('#tab-signup');
const tabIndicator  = $('#tab-indicator');
const loginError    = $('#login-error');
const signupError   = $('#signup-error');
const chatMessages  = $('#chat-messages');
const chatInput     = $('#chat-input');
const btnSend       = $('#btn-send');
const btnNewChat    = $('#btn-new-chat');
const btnLogout     = $('#btn-logout');
const sessionList   = $('#session-list');
const welcomeScreen = $('#welcome-screen');
const userName      = $('#user-name');
const userAvatar    = $('#user-avatar');
const sidebar       = $('#sidebar');
const sidebarToggle = $('#sidebar-toggle');

// ═══════════════════════════════════════════════════════════════
//  ROUTING
// ═══════════════════════════════════════════════════════════════
function navigate(page) {
    authPage.classList.remove('active');
    chatPage.classList.remove('active');
    if (page === 'auth') {
        authPage.classList.add('active');
    } else {
        chatPage.classList.add('active');
        updateUserUI();
        loadSessions();
    }
}

// Check auth on load
function init() {
    if (state.token && state.user) {
        navigate('chat');
    } else {
        navigate('auth');
    }
}

// ═══════════════════════════════════════════════════════════════
//  API HELPER
// ═══════════════════════════════════════════════════════════════
async function api(path, options = {}) {
    const headers = { 'Content-Type': 'application/json' };
    if (state.token) {
        headers['Authorization'] = `Bearer ${state.token}`;
    }

    const res = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers: { ...headers, ...options.headers },
    });

    if (res.status === 401) {
        // Token expired
        logout();
        throw new Error('Session expired. Please sign in again.');
    }

    const data = await res.json();
    if (!res.ok) {
        throw new Error(data.detail || 'Something went wrong');
    }
    return data;
}

// ═══════════════════════════════════════════════════════════════
//  AUTH — TABS
// ═══════════════════════════════════════════════════════════════
tabLogin.addEventListener('click', () => switchTab('login'));
tabSignup.addEventListener('click', () => switchTab('signup'));

function switchTab(tab) {
    tabLogin.classList.toggle('active', tab === 'login');
    tabSignup.classList.toggle('active', tab === 'signup');
    tabIndicator.classList.toggle('right', tab === 'signup');
    loginForm.classList.toggle('active', tab === 'login');
    signupForm.classList.toggle('active', tab === 'signup');
    loginError.textContent = '';
    signupError.textContent = '';
}

// ═══════════════════════════════════════════════════════════════
//  AUTH — LOGIN
// ═══════════════════════════════════════════════════════════════
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    loginError.textContent = '';
    const btn = $('#btn-login');
    setLoading(btn, true);

    try {
        const data = await api('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify({
                email: $('#login-email').value,
                password: $('#login-password').value,
            }),
        });

        state.token = data.access_token;
        state.user = data.user;
        localStorage.setItem('nexus_token', data.access_token);
        localStorage.setItem('nexus_user', JSON.stringify(data.user));
        navigate('chat');
    } catch (err) {
        loginError.textContent = err.message;
    } finally {
        setLoading(btn, false);
    }
});

// ═══════════════════════════════════════════════════════════════
//  AUTH — SIGNUP
// ═══════════════════════════════════════════════════════════════
signupForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    signupError.textContent = '';
    const btn = $('#btn-signup');
    setLoading(btn, true);

    try {
        const data = await api('/api/auth/signup', {
            method: 'POST',
            body: JSON.stringify({
                email: $('#signup-email').value,
                password: $('#signup-password').value,
                full_name: $('#signup-name').value || null,
            }),
        });

        state.token = data.access_token;
        state.user = data.user;
        localStorage.setItem('nexus_token', data.access_token);
        localStorage.setItem('nexus_user', JSON.stringify(data.user));
        navigate('chat');
    } catch (err) {
        signupError.textContent = err.message;
    } finally {
        setLoading(btn, false);
    }
});

// ═══════════════════════════════════════════════════════════════
//  LOGOUT
// ═══════════════════════════════════════════════════════════════
function logout() {
    state.token = null;
    state.user = null;
    state.currentSessionId = null;
    state.sessions = [];
    localStorage.removeItem('nexus_token');
    localStorage.removeItem('nexus_user');
    navigate('auth');
}
btnLogout.addEventListener('click', logout);

// ═══════════════════════════════════════════════════════════════
//  USER UI
// ═══════════════════════════════════════════════════════════════
function updateUserUI() {
    if (state.user) {
        const name = state.user.full_name || state.user.email;
        userName.textContent = name;
        userAvatar.textContent = (name[0] || 'U').toUpperCase();
    }
}

// ═══════════════════════════════════════════════════════════════
//  SESSIONS
// ═══════════════════════════════════════════════════════════════
async function loadSessions() {
    try {
        const sessions = await api('/api/chat/sessions');
        state.sessions = sessions;
        renderSessions();
    } catch (err) {
        console.error('Failed to load sessions:', err);
    }
}

function renderSessions() {
    sessionList.innerHTML = '';
    state.sessions.forEach((s) => {
        const el = document.createElement('div');
        el.className = `session-item ${s.id === state.currentSessionId ? 'active' : ''}`;
        el.textContent = s.title || 'New Conversation';
        el.addEventListener('click', () => loadSession(s.id));
        sessionList.appendChild(el);
    });
}

async function loadSession(sessionId) {
    try {
        state.currentSessionId = sessionId;
        renderSessions();
        const session = await api(`/api/chat/sessions/${sessionId}`);
        clearMessages();
        if (session.messages && session.messages.length > 0) {
            welcomeScreen.style.display = 'none';
            session.messages.forEach((m) => appendMessage(m.role, m.content));
        } else {
            welcomeScreen.style.display = 'flex';
        }
        scrollToBottom();
    } catch (err) {
        console.error('Failed to load session:', err);
    }
}

async function createNewSession() {
    try {
        const session = await api('/api/chat/sessions', { method: 'POST' });
        state.sessions.unshift(session);
        state.currentSessionId = session.id;
        renderSessions();
        clearMessages();
        welcomeScreen.style.display = 'flex';
    } catch (err) {
        console.error('Failed to create session:', err);
    }
}

btnNewChat.addEventListener('click', createNewSession);

// ═══════════════════════════════════════════════════════════════
//  CHAT — MESSAGING
// ═══════════════════════════════════════════════════════════════
chatInput.addEventListener('input', () => {
    btnSend.disabled = !chatInput.value.trim();
    // Auto-resize
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 150) + 'px';
});

chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        if (chatInput.value.trim()) sendMessage();
    }
});

btnSend.addEventListener('click', () => {
    if (chatInput.value.trim()) sendMessage();
});

async function sendMessage() {
    const text = chatInput.value.trim();
    if (!text || state.isLoading) return;

    state.isLoading = true;
    chatInput.value = '';
    chatInput.style.height = 'auto';
    btnSend.disabled = true;

    // Hide welcome
    welcomeScreen.style.display = 'none';

    // Show user message
    appendMessage('user', text);
    scrollToBottom();

    // Show thinking indicator
    const thinkingEl = showThinking();

    try {
        const res = await api('/api/chat/message', {
            method: 'POST',
            body: JSON.stringify({
                message: text,
                session_id: state.currentSessionId,
            }),
        });

        // Update session ID if it was created fresh
        if (res.session_id && res.session_id !== state.currentSessionId) {
            state.currentSessionId = res.session_id;
            loadSessions(); // Refresh session list
        }

        // Remove thinking, show response
        removeThinking(thinkingEl);
        appendMessage('assistant', res.message);
    } catch (err) {
        removeThinking(thinkingEl);
        appendMessage('assistant', `⚠️ Error: ${err.message}`);
    } finally {
        state.isLoading = false;
        scrollToBottom();
    }
}

// ═══════════════════════════════════════════════════════════════
//  MESSAGE RENDERING
// ═══════════════════════════════════════════════════════════════
function appendMessage(role, content) {
    const msgEl = document.createElement('div');
    msgEl.className = `message ${role}`;

    const avatarLabel = role === 'user'
        ? (state.user?.full_name?.[0] || state.user?.email?.[0] || 'U').toUpperCase()
        : 'N';

    msgEl.innerHTML = `
        <div class="message-avatar">${avatarLabel}</div>
        <div class="message-content">
            <div class="message-role">${role === 'user' ? 'You' : 'NexusAI'}</div>
            <div class="message-text">${formatMessage(content)}</div>
        </div>
    `;

    chatMessages.appendChild(msgEl);
}

function formatMessage(text) {
    // Very basic markdown-like formatting
    let formatted = escapeHTML(text);

    // Code blocks: ```...```
    formatted = formatted.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
        return `<pre><code>${code.trim()}</code></pre>`;
    });

    // Inline code: `...`
    formatted = formatted.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Bold: **...**
    formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // Line breaks
    formatted = formatted.replace(/\n/g, '<br>');

    return formatted;
}

function escapeHTML(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function clearMessages() {
    // Keep welcome screen, remove everything else
    const children = Array.from(chatMessages.children);
    children.forEach((c) => {
        if (c !== welcomeScreen) c.remove();
    });
}

// ═══════════════════════════════════════════════════════════════
//  THINKING INDICATOR
// ═══════════════════════════════════════════════════════════════
function showThinking() {
    const el = document.createElement('div');
    el.className = 'thinking-indicator';
    el.innerHTML = `
        <div class="message-avatar" style="background: var(--gradient-brand); color: white;">N</div>
        <div class="thinking-dots">
            <div class="thinking-dot"></div>
            <div class="thinking-dot"></div>
            <div class="thinking-dot"></div>
        </div>
    `;
    chatMessages.appendChild(el);
    scrollToBottom();
    return el;
}

function removeThinking(el) {
    if (el && el.parentNode) el.remove();
}

// ═══════════════════════════════════════════════════════════════
//  QUICK PROMPTS
// ═══════════════════════════════════════════════════════════════
$$('.quick-prompt').forEach((btn) => {
    btn.addEventListener('click', () => {
        chatInput.value = btn.dataset.prompt;
        btnSend.disabled = false;
        chatInput.focus();
        sendMessage();
    });
});

// ═══════════════════════════════════════════════════════════════
//  SCROLL
// ═══════════════════════════════════════════════════════════════
function scrollToBottom() {
    requestAnimationFrame(() => {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    });
}

// ═══════════════════════════════════════════════════════════════
//  LOADING BUTTON STATE
// ═══════════════════════════════════════════════════════════════
function setLoading(btn, loading) {
    const text = btn.querySelector('.btn-text');
    const spinner = btn.querySelector('.btn-spinner');
    if (loading) {
        btn.disabled = true;
        text.style.opacity = '0';
        spinner.hidden = false;
    } else {
        btn.disabled = false;
        text.style.opacity = '1';
        spinner.hidden = true;
    }
}

// ═══════════════════════════════════════════════════════════════
//  MOBILE SIDEBAR
// ═══════════════════════════════════════════════════════════════
sidebarToggle.addEventListener('click', () => {
    sidebar.classList.toggle('open');
});

// Close sidebar when clicking outside on mobile
document.addEventListener('click', (e) => {
    if (window.innerWidth <= 768 && sidebar.classList.contains('open')) {
        if (!sidebar.contains(e.target) && e.target !== sidebarToggle) {
            sidebar.classList.remove('open');
        }
    }
});

// ═══════════════════════════════════════════════════════════════
//  INIT
// ═══════════════════════════════════════════════════════════════
init();
