/* ═══════════════════════════════════════════════════════════════
   NexusAI — Frontend Application Logic
   Connects to FastAPI backend at /api/auth/* and /api/chat/*
   Features: chat, streaming, edit prompt, regenerate, rename/delete sessions
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

function init() {
    if (state.token && state.user) {
        navigate('chat');
    } else {
        navigate('auth');
    }
}

// ── API Helper ──────────────────────────────────────────────────
async function api(path, options = {}) {
    const headers = { 'Content-Type': 'application/json' };
    if (state.token) headers['Authorization'] = `Bearer ${state.token}`;

    const res = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers: { ...headers, ...options.headers },
    });

    if (res.status === 401) {
        logout();
        throw new Error('Session expired.');
    }
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
    loginError.textContent = ''; signupError.textContent = '';
}

loginForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = $('#btn-login'); setLoading(btn, true);
    try {
        const data = await api('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email: $('#login-email').value, password: $('#login-password').value }),
        });
        state.token = data.access_token; state.user = data.user;
        localStorage.setItem('nexus_token', data.access_token);
        localStorage.setItem('nexus_user', JSON.stringify(data.user));
        navigate('chat');
    } catch (err) { loginError.textContent = err.message; }
    finally { setLoading(btn, false); }
});

signupForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = $('#btn-signup'); setLoading(btn, true);
    try {
        const data = await api('/api/auth/signup', {
            method: 'POST',
            body: JSON.stringify({ email: $('#signup-email').value, password: $('#signup-password').value, full_name: $('#signup-name').value || null }),
        });
        state.token = data.access_token; state.user = data.user;
        localStorage.setItem('nexus_token', data.access_token);
        localStorage.setItem('nexus_user', JSON.stringify(data.user));
        navigate('chat');
    } catch (err) { signupError.textContent = err.message; }
    finally { setLoading(btn, false); }
});

function logout() {
    state.token = null; state.user = null; state.currentSessionId = null;
    localStorage.removeItem('nexus_token'); localStorage.removeItem('nexus_user');
    navigate('auth');
}
btnLogout.addEventListener('click', logout);

function updateUserUI() {
    if (state.user) {
        const name = state.user.full_name || state.user.email;
        userName.textContent = name; userAvatar.textContent = (name[0] || 'U').toUpperCase();
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
    } catch (err) { console.error('Sessions pull failed:', err); }
}

function renderSessions() {
    sessionList.innerHTML = '';
    state.sessions.forEach((s) => {
        const el = document.createElement('div');
        el.className = `session-item ${s.id === state.currentSessionId ? 'active' : ''}`;
        el.innerHTML = `
            <span class="session-title">${escapeHTML(s.title || 'New Conversation')}</span>
            <span class="session-actions">
                <button class="session-action-btn rename" title="Rename"><svg viewBox="0 0 20 20" fill="currentColor"><path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"/></svg></button>
                <button class="session-action-btn delete" title="Delete"><svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd"/></svg></button>
            </span>
        `;
        el.querySelector('.session-title').addEventListener('click', () => loadSession(s.id));
        el.querySelector('.rename').addEventListener('click', (e) => { e.stopPropagation(); startRenameSession(el, s); });
        el.querySelector('.delete').addEventListener('click', (e) => { e.stopPropagation(); confirmDeleteSession(s.id); });
        sessionList.appendChild(el);
    });
}

function startRenameSession(el, session) {
    const titleSpan = el.querySelector('.session-title');
    const input = document.createElement('input');
    input.type = 'text'; input.className = 'session-rename-input'; input.value = session.title || 'New Conversation';
    titleSpan.replaceWith(input); input.focus(); input.select();
    const finish = async () => {
        const nt = input.value.trim() || session.title;
        try {
            await api(`/api/chat/sessions/${session.id}/rename`, { method: 'PUT', body: JSON.stringify({ title: nt }) });
            session.title = nt;
        } catch (err) { console.error('Rename err:', err); }
        loadSessions();
    };
    input.addEventListener('blur', finish);
    input.addEventListener('keydown', (e) => { if (e.key === 'Enter') input.blur(); });
}

function confirmDeleteSession(sessionId) {
    const overlay = document.createElement('div'); el.className = 'modal-overlay';
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
        <div class="modal-card">
            <h3>Delete conversation?</h3><p>This will permanently remove this chat.</p>
            <div class="modal-buttons">
                <button class="modal-btn-cancel">Cancel</button><button class="modal-btn-delete">Delete</button>
            </div>
        </div>
    `;
    overlay.querySelector('.modal-btn-cancel').addEventListener('click', () => overlay.remove());
    overlay.querySelector('.modal-btn-delete').addEventListener('click', async () => {
        try {
            await api(`/api/chat/sessions/${sessionId}`, { method: 'DELETE' });
            if (state.currentSessionId === sessionId) { state.currentSessionId = null; clearMessages(); welcomeScreen.style.display = 'flex'; }
            loadSessions();
        } catch (err) { console.error('Del err:', err); }
        overlay.remove();
    });
    document.body.appendChild(overlay);
}

async function loadSession(sessionId) {
    try {
        state.currentSessionId = sessionId; renderSessions();
        const session = await api(`/api/chat/sessions/${sessionId}`);
        clearMessages(); state.currentMessages = [];
        if (session.messages?.length) {
            welcomeScreen.style.display = 'none';
            session.messages.forEach((m) => {
                state.currentMessages.push({ role: m.role, content: m.content });
                appendMessage(m.role, m.content);
            });
        } else { welcomeScreen.style.display = 'flex'; }
        scrollToBottom();
    } catch (err) { console.error('Load session err:', err); }
}

async function createNewSession() {
    try {
        const session = await api('/api/chat/sessions', { method: 'POST' });
        state.currentSessionId = session.id; loadSessions(); clearMessages(); welcomeScreen.style.display = 'flex';
    } catch (err) { console.error('Create session err:', err); }
}
btnNewChat.addEventListener('click', createNewSession);

// ═══════════════════════════════════════════════════════════════
//  CHAT & STREAMING
// ═══════════════════════════════════════════════════════════════
chatInput.addEventListener('input', () => {
    btnSend.disabled = !chatInput.value.trim();
    chatInput.style.height = 'auto'; chatInput.style.height = Math.min(chatInput.scrollHeight, 150) + 'px';
});

chatInput.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); if (chatInput.value.trim()) sendMessage(); } });
btnSend.addEventListener('click', () => { if (chatInput.value.trim()) sendMessage(); });

async function sendMessage(overrideText = null) {
    const text = overrideText || chatInput.value.trim();
    if (!text || state.isLoading) return;

    state.isLoading = true; welcomeScreen.style.display = 'none';
    if (!overrideText) { chatInput.value = ''; chatInput.style.height = 'auto'; }
    btnSend.disabled = true;

    appendMessage('user', text); state.currentMessages.push({ role: 'user', content: text });
    scrollToBottom();

    // ── Pre-create Assistant Bubble for Streaming ──────────────
    const assistantMsgEl = createMessageElement('assistant', '');
    chatMessages.appendChild(assistantMsgEl);
    const contentDiv = assistantMsgEl.querySelector('.message-text');
    const thinkingEl = showThinkingInline(assistantMsgEl);
    scrollToBottom();

    let fullContent = "";
    try {
        const response = await fetch(`${API_BASE}/api/chat/message`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${state.token}` },
            body: JSON.stringify({ message: text, session_id: state.currentSessionId })
        });

        if (!response.ok) throw new Error("Stream failed");

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n\n");
            buffer = lines.pop(); // Keep incomplete line in buffer

            for (const line of lines) {
                if (line.startsWith("data: ")) {
                    const jsonStr = line.replace("data: ", "").trim();
                    if (!jsonStr) continue;
                    try {
                        const data = JSON.parse(jsonStr);
                        if (data.type === "token") {
                            if (thinkingEl) { thinkingEl.remove(); }
                            fullContent += data.content;
                            contentDiv.innerHTML = formatMessage(fullContent);
                            scrollToBottom();
                        }
                        if (data.type === "done") {
                             loadSessions(); // Update titles
                        }
                    } catch (e) { console.error("JSON parse err in stream:", e); }
                }
            }
        }
        state.currentMessages.push({ role: 'assistant', content: fullContent });
    } catch (err) {
        if (thinkingEl) thinkingEl.remove();
        contentDiv.innerHTML = `<span style="color:#ef4444">⚠️ Error: ${err.message}</span>`;
    } finally {
        state.isLoading = false; btnSend.disabled = false; scrollToBottom();
    }
}

// ═══════════════════════════════════════════════════════════════
//  EDIT & REGENERATE
// ═══════════════════════════════════════════════════════════════
function startEditMessage(msgEl, originalText, msgIndex) {
    const textDiv = msgEl.querySelector('.message-text');
    const actionsDiv = msgEl.querySelector('.message-actions');
    if (actionsDiv) actionsDiv.style.display = 'none';
    const oldHTML = textDiv.innerHTML; textDiv.innerHTML = '';

    const textarea = document.createElement('textarea'); textarea.className = 'edit-area'; textarea.value = originalText;
    textDiv.appendChild(textarea);
    const btnRow = document.createElement('div'); btnRow.className = 'edit-buttons';
    btnRow.innerHTML = `<button class="edit-btn-cancel">Cancel</button><button class="edit-btn-save">Save & Send</button>`;
    textDiv.appendChild(btnRow); textarea.focus();

    btnRow.querySelector('.edit-btn-cancel').addEventListener('click', () => { textDiv.innerHTML = oldHTML; if (actionsDiv) actionsDiv.style.display = ''; });
    btnRow.querySelector('.edit-btn-save').addEventListener('click', async () => {
        const nt = textarea.value.trim(); if (!nt) return;
        removeMessagesAfterIndex(msgIndex); state.currentMessages.splice(msgIndex);
        sendMessage(nt);
    });
}

function removeMessagesAfterIndex(idx) {
    const all = Array.from(chatMessages.children).filter(c => c !== welcomeScreen && c.classList.contains('message'));
    for (let i = all.length - 1; i >= idx; i--) all[i].remove();
}

// ═══════════════════════════════════════════════════════════════
//  RENDERING & MARKDOWN
// ═══════════════════════════════════════════════════════════════
function createMessageElement(role, content) {
    const el = document.createElement('div'); el.className = `message ${role}`;
    const avatar = role === 'user' ? (state.user?.email?.[0] || 'U').toUpperCase() : 'N';
    const actions = role === 'user' 
        ? `<div class="message-actions"><button class="msg-action-btn edit-btn" title="Edit"><svg viewBox="0 0 20 20" fill="currentColor"><path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"/></svg>Edit</button></div>`
        : `<div class="message-actions"><button class="msg-action-btn regenerate-btn" title="Regenerate"><svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd"/></svg>Regenerate</button></div>`;

    el.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            <div class="message-role">${role === 'user' ? 'You' : 'NexusAI'}</div>
            <div class="message-text">${formatMessage(content)}</div>
            ${actions}
        </div>
    `;

    if (role === 'user') {
        el.querySelector('.edit-btn').addEventListener('click', () => {
            const all = Array.from(chatMessages.children).filter(c => c !== welcomeScreen && c.classList.contains('message'));
            startEditMessage(el, content, all.indexOf(el));
        });
    } else {
        el.querySelector('.regenerate-btn').addEventListener('click', () => {
            const all = Array.from(chatMessages.children).filter(c => c !== welcomeScreen && c.classList.contains('message'));
            const idx = all.indexOf(el);
            const userMsg = state.currentMessages[idx-1];
            if (userMsg) { removeMessagesAfterIndex(idx-1); state.currentMessages.splice(idx-1); sendMessage(userMsg.content); }
        });
    }
    return el;
}

function appendMessage(role, content) {
    chatMessages.appendChild(createMessageElement(role, content));
}

function formatMessage(text) {
    if (!text) return "";
    let h = escapeHTML(text);

    // Headers: ### something
    h = h.replace(/^### (.*$)/gm, '<h3 class="md-h3">$1</h3>');

    // Code blocks
    h = h.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => `<pre><code>${code.trim()}</code></pre>`);
    h = h.replace(/`([^`]+)`/g, '<code>$1</code>');
    h = h.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // Tables
    h = h.replace(/((?:^\|.+\|$\n?)+)/gm, (block) => {
        const lines = block.trim().split('\n').filter(l => l.trim());
        if (lines.length < 2) return block;
        const parse = (l) => l.replace(/^\|/, '').replace(/\|$/, '').split('|').map(c => c.trim());
        const header = parse(lines[0]);
        let out = '<table><thead><tr>' + header.map(c => `<th>${c}</th>`).join('') + '</tr></thead><tbody>';
        lines.slice(2).forEach(line => { out += '<tr>' + parse(line).map(c => `<td>${c}</td>`).join('') + '</tr>'; });
        return out + '</tbody></table>';
    });

    // Lists
    const lines = h.split('\n'); let res = []; let inL = false;
    for (const l of lines) {
        const m = l.match(/^(\s*)[-*]\s+(.+)/);
        if (m) { if (!inL) { res.push('<ul>'); inL = true; } res.push(`<li>${m[2]}</li>`); }
        else { if (inL) { res.push('</ul>'); inL = false; } res.push(l); }
    }
    if (inL) res.push('</ul>');
    return res.join('\n').replace(/\n/g, '<br>');
}

function escapeHTML(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
function clearMessages() { Array.from(chatMessages.children).forEach(c => { if (c !== welcomeScreen) c.remove(); }); }

function showThinkingInline(parent) {
    const el = document.createElement('div'); el.className = 'inline-thinking';
    el.innerHTML = `<div class="thinking-dot"></div><div class="thinking-dot"></div><div class="thinking-dot"></div>`;
    parent.querySelector('.message-text').appendChild(el);
    return el;
}

function scrollToBottom() { requestAnimationFrame(() => { chatMessages.scrollTop = chatMessages.scrollHeight; }); }
function setLoading(b, l) {
    const t = b.querySelector('.btn-text'); const s = b.querySelector('.btn-spinner');
    if (l) { b.disabled = true; t.style.opacity = '0'; s.hidden = false; }
    else { b.disabled = false; t.style.opacity = '1'; s.hidden = true; }
}

sidebarToggle.addEventListener('click', () => sidebar.classList.toggle('open'));
init();
