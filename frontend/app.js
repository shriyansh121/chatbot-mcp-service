/* ═══════════════════════════════════════════════════════════════
   NexusAI — Frontend Application Logic
   Connects to FastAPI backend with real-time streaming (SSE)
   ═══════════════════════════════════════════════════════════════ */

const API_BASE = window.location.origin;

// ── State ────────────────────────────────────────────────────────
const state = {
    token: localStorage.getItem('nexus_token') || null,
    user: JSON.parse(localStorage.getItem('nexus_user') || 'null'),
    currentSessionId: null,
    sessions: [],
    isLoading: false,
    currentMessages: [],
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
//  ROUTING & INIT
// ═══════════════════════════════════════════════════════════════
function navigate(page) {
    authPage.classList.remove('active'); chatPage.classList.remove('active');
    if (page === 'auth') { authPage.classList.add('active'); }
    else { chatPage.classList.add('active'); updateUserUI(); loadSessions(); }
}

function init() { if (state.token && state.user) { navigate('chat'); } else { navigate('auth'); } }

// ── API Helper (Non-streaming) ──────────────────────────────────
async function api(path, options = {}) {
    const headers = { 'Content-Type': 'application/json' };
    if (state.token) headers['Authorization'] = `Bearer ${state.token}`;
    const res = await fetch(`${API_BASE}${path}`, { ...options, headers: { ...headers, ...options.headers } });
    if (res.status === 401) { logout(); throw new Error('Session expired'); }
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Generic error');
    return data;
}

// ═══════════════════════════════════════════════════════════════
//  AUTH
// ═══════════════════════════════════════════════════════════════
tabLogin.addEventListener('click', () => switchTab('login'));
tabSignup.addEventListener('click', () => switchTab('signup'));
function switchTab(tab) {
    tabLogin.classList.toggle('active', tab === 'login');
    tabSignup.classList.toggle('active', tab === 'signup');
    tabIndicator.classList.toggle('right', tab === 'signup');
    loginForm.classList.toggle('active', tab === 'login');
    signupForm.classList.toggle('active', tab === 'signup');
}
loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
        const data = await api('/api/auth/login', { method: 'POST', body: JSON.stringify({ email: $('#login-email').value, password: $('#login-password').value }) });
        state.token = data.access_token; state.user = data.user;
        localStorage.setItem('nexus_token', state.token); localStorage.setItem('nexus_user', JSON.stringify(state.user));
        navigate('chat');
    } catch (err) { alert(err.message); }
});
signupForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    try {
        const data = await api('/api/auth/signup', { method: 'POST', body: JSON.stringify({ email: $('#signup-email').value, password: $('#signup-password').value, full_name: $('#signup-name').value || null })});
        state.token = data.access_token; state.user = data.user;
        localStorage.setItem('nexus_token', state.token); localStorage.setItem('nexus_user', JSON.stringify(state.user));
        navigate('chat');
    } catch (err) { alert(err.message); }
});
function logout() { localStorage.clear(); location.reload(); }
btnLogout.addEventListener('click', logout);
function updateUserUI() {
    if (state.user) {
        const n = state.user.full_name || state.user.email;
        userName.textContent = n; userAvatar.textContent = (n[0] || 'U').toUpperCase();
    }
}

// ═══════════════════════════════════════════════════════════════
//  SESSIONS
// ═══════════════════════════════════════════════════════════════
async function loadSessions() {
    try {
        state.sessions = await api('/api/chat/sessions');
        renderSessions();
    } catch (err) { console.error('Sessions err:', err); }
}
function renderSessions() {
    sessionList.innerHTML = '';
    state.sessions.forEach((s) => {
        const el = document.createElement('div'); el.className = `session-item ${s.id === state.currentSessionId ? 'active' : ''}`;
        el.innerHTML = `
            <span class="session-title">${escapeHTML(s.title || 'New Chat')}</span>
            <span class="session-actions">
                <button class="session-action-btn rename"><svg viewBox="0 0 20 20" fill="currentColor"><path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"/></svg></button>
                <button class="session-action-btn delete"><svg viewBox="0 0 20 20" fill="currentColor"><path d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"/></svg></button>
            </span>
        `;
        el.querySelector('.session-title').onclick = () => loadSession(s.id);
        el.querySelector('.rename').onclick = (e) => { e.stopPropagation(); startRename(el, s); };
        el.querySelector('.delete').onclick = (e) => { e.stopPropagation(); confirmDelete(s.id); };
        sessionList.appendChild(el);
    });
}
function startRename(el, s) {
    const orig = el.querySelector('.session-title');
    const input = document.createElement('input'); input.className = 'session-rename-input'; input.value = s.title;
    orig.replaceWith(input); input.focus();
    input.onblur = async () => {
        const nt = input.value.trim() || s.title;
        try { await api(`/api/chat/sessions/${s.id}/rename`, { method: 'PUT', body: JSON.stringify({ title: nt })}); s.title = nt; } catch {}
        loadSessions();
    };
    input.onkeydown = (e) => { if (e.key === 'Enter') input.blur(); };
}
function confirmDelete(id) {
    if (confirm('Delete this conversation?')) {
        api(`/api/chat/sessions/${id}`, { method: 'DELETE' })
            .then(() => { if (state.currentSessionId === id) { state.currentSessionId = null; clearChat(); } loadSessions(); });
    }
}
async function loadSession(id) {
    state.currentSessionId = id; renderSessions();
    const s = await api(`/api/chat/sessions/${id}`);
    clearChat(); state.currentMessages = [];
    if (s.messages?.length) {
        welcomeScreen.style.display = 'none';
        s.messages.forEach(m => { state.currentMessages.push(m); appendMessage(m.role, m.content); });
    } else { welcomeScreen.style.display = 'flex'; }
    scrollToBottom();
}
btnNewChat.onclick = async () => {
    const s = await api('/api/chat/sessions', { method: 'POST' });
    state.currentSessionId = s.id; loadSessions(); clearChat(); welcomeScreen.style.display = 'flex';
};

// ═══════════════════════════════════════════════════════════════
//  CHAT & STREAMING
// ═══════════════════════════════════════════════════════════════
function clearChat() { chatMessages.querySelectorAll('.message').forEach(m => m.remove()); welcomeScreen.style.display = 'flex'; }

btnSend.onclick = () => sendMessage();
chatInput.onkeydown = (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); } };

async function sendMessage(overrideText = null) {
    const text = overrideText || chatInput.value.trim();
    if (!text || state.isLoading) return;

    state.isLoading = true; welcomeScreen.style.display = 'none';
    if (!overrideText) chatInput.value = '';
    
    appendMessage('user', text);
    state.currentMessages.push({ role: 'user', content: text });
    scrollToBottom();

    // Setup assistant bubble
    const msgEl = appendMessage('assistant', '');
    const contentDiv = msgEl.querySelector('.message-text');
    const thinking = showThinking(contentDiv);
    
    let full = "";
    try {
        const response = await fetch(`${API_BASE}/api/chat/message`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${state.token}` },
            body: JSON.stringify({ message: text, session_id: state.currentSessionId })
        });

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });
            
            const chunks = buffer.split('\n\n');
            buffer = chunks.pop();

            for (const chunk of chunks) {
                const line = chunk.trim();
                // Fix: Robust data picking
                if (line.startsWith('data: ')) {
                    const jsonStr = line.substring(6).trim();
                    if (!jsonStr) continue;
                    try {
                        const data = JSON.parse(jsonStr);
                        if (data.type === 'token') {
                            if (thinking) thinking.remove();
                            full += data.content;
                            contentDiv.innerHTML = formatMessage(full);
                            scrollToBottom();
                        } else if (data.type === 'done') {
                            loadSessions(); // update titles
                        }
                    } catch (e) { console.warn('Stream parse err:', line); }
                }
            }
        }
        state.currentMessages.push({ role: 'assistant', content: full });
    } catch (err) {
        contentDiv.innerHTML = `<span style="color:#ef4444">Error: ${err.message}</span>`;
    } finally {
        state.isLoading = false; scrollToBottom();
    }
}

// ═══════════════════════════════════════════════════════════════
//  RENDERING UTILS
// ═══════════════════════════════════════════════════════════════
function appendMessage(role, content) {
    const el = document.createElement('div'); el.className = `message ${role}`;
    const avatar = role === 'user' ? (state.user?.email?.[0] || 'U').toUpperCase() : 'N';
    const actions = role === 'user' 
        ? `<button class="msg-action-btn edit-msg">Edit</button>` 
        : `<button class="msg-action-btn regen-msg">Regenerate</button>`;

    el.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            <div class="message-role">${role === 'user' ? 'You' : 'NexusAI'}</div>
            <div class="message-text">${formatMessage(content)}</div>
            <div class="message-actions">${actions}</div>
        </div>
    `;

    if (role === 'user') {
        el.querySelector('.edit-msg').onclick = () => startEdit(el, content);
    } else {
        el.querySelector('.regen-msg').onclick = () => regenerate(el);
    }

    chatMessages.appendChild(el);
    return el;
}

function startEdit(el, content) {
    const textDiv = el.querySelector('.message-text');
    const old = textDiv.innerHTML;
    textDiv.innerHTML = `<textarea class="edit-area">${content}</textarea><div class="edit-buttons"><button class="save">Save</button><button class="cancel">Cancel</button></div>`;
    textDiv.querySelector('.cancel').onclick = () => textDiv.innerHTML = old;
    textDiv.querySelector('.save').onclick = () => {
        const nt = textDiv.querySelector('textarea').value.trim();
        if (nt) { removeTrailing(el); sendMessage(nt); }
    };
}

function regenerate(el) {
    const idx = Array.from(chatMessages.children).indexOf(el) - 1; // get index of user message before this bubble
    const userMsgEl = chatMessages.children[idx]; // the user message
    if (userMsgEl && userMsgEl.classList.contains('user')) {
        const text = state.currentMessages[idx - 1]?.content; // Note: currentMessages is 1-indexed for some reason in my logic, let's just use the DOM text
        // Actually, let's just find the last user message
        const userMsgText = state.currentMessages.filter(m => m.role === 'user').pop()?.content;
        removeTrailing(userMsgEl); // Remove the user message and everything after
        sendMessage(userMsgText);
    }
}

function removeTrailing(el) {
    while (el.nextSibling) el.nextSibling.remove();
    el.remove();
}

function formatMessage(t) {
    if (!t) return "";
    let h = escapeHTML(t);
    h = h.replace(/^### (.*$)/gm, '<h3 class="md-h3">$1</h3>');
    h = h.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, l, c) => `<pre><code>${c.trim()}</code></pre>`);
    h = h.replace(/`([^`]+)`/g, '<code>$1</code>');
    h = h.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
    return h.replace(/\n/g, '<br>');
}
function escapeHTML(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
function showThinking(div) { const t = document.createElement('div'); t.className = 'inline-thinking'; t.innerHTML = '<span>.</span><span>.</span><span>.</span>'; div.appendChild(t); return t; }
function scrollToBottom() { chatMessages.scrollTop = chatMessages.scrollHeight; }

sidebarToggle.onclick = () => sidebar.classList.toggle('open');
init();
