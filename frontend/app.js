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
    currentMessages: [],   // [{role, content}, ...]
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
    // Bind quick-prompt buttons on load
    bindQuickPrompts();
}

// ── API Helper (Non-streaming, JSON) ────────────────────────────
async function api(path, options = {}) {
    const headers = { 'Content-Type': 'application/json' };
    if (state.token) headers['Authorization'] = `Bearer ${state.token}`;
    const res = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers: { ...headers, ...options.headers },
    });
    if (res.status === 401) { logout(); throw new Error('Session expired'); }
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Request failed');
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
        const data = await api('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify({
                email: $('#login-email').value,
                password: $('#login-password').value,
            }),
        });
        state.token = data.access_token;
        state.user = data.user;
        localStorage.setItem('nexus_token', state.token);
        localStorage.setItem('nexus_user', JSON.stringify(state.user));
        navigate('chat');
    } catch (err) { alert(err.message); }
});

signupForm.addEventListener('submit', async (e) => {
    e.preventDefault();
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
        localStorage.setItem('nexus_token', state.token);
        localStorage.setItem('nexus_user', JSON.stringify(state.user));
        navigate('chat');
    } catch (err) { alert(err.message); }
});

function logout() { localStorage.clear(); location.reload(); }
btnLogout.addEventListener('click', logout);

function updateUserUI() {
    if (state.user) {
        const n = state.user.full_name || state.user.email;
        userName.textContent = n;
        userAvatar.textContent = (n[0] || 'U').toUpperCase();
    }
}

// ═══════════════════════════════════════════════════════════════
//  SESSIONS
// ═══════════════════════════════════════════════════════════════
async function loadSessions() {
    try {
        state.sessions = await api('/api/chat/sessions');
        renderSessions();
    } catch (err) { console.error('Sessions load failed:', err); }
}

function renderSessions() {
    sessionList.innerHTML = '';
    state.sessions.forEach((s) => {
        const el = document.createElement('div');
        el.className = `session-item ${s.id === state.currentSessionId ? 'active' : ''}`;
        el.innerHTML = `
            <span class="session-title">${escapeHTML(s.title || 'New Chat')}</span>
            <span class="session-actions">
                <button class="session-action-btn rename" title="Rename"><svg viewBox="0 0 20 20" fill="currentColor"><path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"/></svg></button>
                <button class="session-action-btn delete" title="Delete"><svg viewBox="0 0 20 20" fill="currentColor"><path d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"/></svg></button>
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
    const input = document.createElement('input');
    input.className = 'session-rename-input';
    input.value = s.title || 'New Chat';
    orig.replaceWith(input);
    input.focus();
    input.select();
    const finish = async () => {
        const nt = input.value.trim() || s.title;
        try {
            await api(`/api/chat/sessions/${s.id}/rename`, {
                method: 'PUT',
                body: JSON.stringify({ title: nt }),
            });
            s.title = nt;
        } catch (err) { console.error('Rename err:', err); }
        loadSessions();
    };
    input.onblur = finish;
    input.onkeydown = (e) => { if (e.key === 'Enter') input.blur(); };
}

function confirmDelete(id) {
    if (!confirm('Delete this conversation?')) return;
    api(`/api/chat/sessions/${id}`, { method: 'DELETE' })
        .then(() => {
            if (state.currentSessionId === id) {
                state.currentSessionId = null;
                clearChat();
            }
            loadSessions();
        })
        .catch(err => console.error('Delete err:', err));
}

async function loadSession(id) {
    state.currentSessionId = id;
    renderSessions();
    try {
        const s = await api(`/api/chat/sessions/${id}`);
        clearChat();
        state.currentMessages = [];
        if (s.messages && s.messages.length) {
            welcomeScreen.style.display = 'none';
            s.messages.forEach((m) => {
                state.currentMessages.push({ role: m.role, content: m.content });
                appendMessage(m.role, m.content);
            });
        } else {
            welcomeScreen.style.display = 'flex';
        }
        scrollToBottom();
    } catch (err) { console.error('Load session err:', err); }
}

btnNewChat.onclick = async () => {
    try {
        const s = await api('/api/chat/sessions', { method: 'POST' });
        state.currentSessionId = s.id;
        state.currentMessages = [];
        loadSessions();
        clearChat();
        welcomeScreen.style.display = 'flex';
    } catch (err) { console.error('Create session err:', err); }
};

// ═══════════════════════════════════════════════════════════════
//  QUICK PROMPT BUTTONS (Welcome screen)
// ═══════════════════════════════════════════════════════════════
function bindQuickPrompts() {
    document.querySelectorAll('.quick-prompt').forEach(btn => {
        btn.addEventListener('click', () => {
            const prompt = btn.getAttribute('data-prompt');
            if (prompt) {
                chatInput.value = prompt;
                sendMessage();
            }
        });
    });
}

// ═══════════════════════════════════════════════════════════════
//  CHAT & STREAMING
// ═══════════════════════════════════════════════════════════════
function clearChat() {
    chatMessages.querySelectorAll('.message').forEach(m => m.remove());
    welcomeScreen.style.display = 'flex';
}

chatInput.addEventListener('input', () => {
    btnSend.disabled = !chatInput.value.trim();
    chatInput.style.height = 'auto';
    chatInput.style.height = Math.min(chatInput.scrollHeight, 150) + 'px';
});

chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});
btnSend.addEventListener('click', () => sendMessage());

async function sendMessage(overrideText = null) {
    const text = overrideText || chatInput.value.trim();
    if (!text || state.isLoading) return;

    state.isLoading = true;
    btnSend.disabled = true;
    welcomeScreen.style.display = 'none';
    if (!overrideText) {
        chatInput.value = '';
        chatInput.style.height = 'auto';
    }

    // If no session yet, create one first
    if (!state.currentSessionId) {
        try {
            const s = await api('/api/chat/sessions', { method: 'POST' });
            state.currentSessionId = s.id;
        } catch (err) {
            console.error('Auto-create session err:', err);
            state.isLoading = false;
            btnSend.disabled = false;
            return;
        }
    }

    // Append user message to UI
    appendMessage('user', text);
    state.currentMessages.push({ role: 'user', content: text });
    scrollToBottom();

    // Create empty assistant bubble for streaming
    const assistantEl = appendMessage('assistant', '');
    const contentDiv = assistantEl.querySelector('.message-text');
    showThinking(contentDiv);
    scrollToBottom();

    let fullResponse = '';

    try {
        const response = await fetch(`${API_BASE}/api/chat/message`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${state.token}`,
            },
            body: JSON.stringify({
                message: text,
                session_id: state.currentSessionId,
            }),
        });

        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let thinkingRemoved = false;

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });

            // Process complete SSE messages (separated by \n\n)
            const parts = buffer.split('\n\n');
            buffer = parts.pop(); // Keep incomplete chunk in buffer

            for (const part of parts) {
                const line = part.trim();
                if (!line.startsWith('data: ')) continue;

                const jsonStr = line.slice(6); // Remove "data: " prefix
                if (!jsonStr) continue;

                try {
                    const data = JSON.parse(jsonStr);

                    if (data.type === 'token' && data.content) {
                        if (!thinkingRemoved) {
                            contentDiv.innerHTML = '';
                            thinkingRemoved = true;
                        }
                        fullResponse += data.content;
                        contentDiv.innerHTML = formatMessage(fullResponse);
                        scrollToBottom();
                    } else if (data.type === 'done') {
                        // Refresh sidebar to show updated title
                        loadSessions();
                    } else if (data.error) {
                        contentDiv.innerHTML = `<span style="color:#ef4444">⚠️ ${data.error}</span>`;
                    }
                } catch (parseErr) {
                    console.warn('SSE parse skip:', jsonStr.substring(0, 80));
                }
            }
        }

        // Save assistant response to local state
        state.currentMessages.push({ role: 'assistant', content: fullResponse });

    } catch (err) {
        contentDiv.innerHTML = `<span style="color:#ef4444">⚠️ Error: ${err.message}</span>`;
    } finally {
        state.isLoading = false;
        btnSend.disabled = false;
        scrollToBottom();
    }
}

// ═══════════════════════════════════════════════════════════════
//  EDIT & REGENERATE
// ═══════════════════════════════════════════════════════════════
function startEdit(msgEl, originalText) {
    const textDiv = msgEl.querySelector('.message-text');
    const actionsDiv = msgEl.querySelector('.message-actions');
    const savedHTML = textDiv.innerHTML;
    if (actionsDiv) actionsDiv.style.display = 'none';

    textDiv.innerHTML = '';
    const ta = document.createElement('textarea');
    ta.className = 'edit-area';
    ta.value = originalText;
    textDiv.appendChild(ta);

    const btnRow = document.createElement('div');
    btnRow.className = 'edit-buttons';
    btnRow.innerHTML = '<button class="edit-btn-cancel">Cancel</button><button class="edit-btn-save">Save & Send</button>';
    textDiv.appendChild(btnRow);
    ta.focus();

    btnRow.querySelector('.edit-btn-cancel').onclick = () => {
        textDiv.innerHTML = savedHTML;
        if (actionsDiv) actionsDiv.style.display = '';
    };

    btnRow.querySelector('.edit-btn-save').onclick = () => {
        const newText = ta.value.trim();
        if (!newText) return;

        // Find index of this message in currentMessages
        const allMsgEls = getAllMessageEls();
        const idx = allMsgEls.indexOf(msgEl);

        // Remove this message and everything after from DOM
        for (let i = allMsgEls.length - 1; i >= idx; i--) {
            allMsgEls[i].remove();
        }
        // Trim currentMessages to before this index
        state.currentMessages.splice(idx);

        // Re-send with edited text
        sendMessage(newText);
    };
}

function regenerate(assistantEl, originalUserText) {
    // Find index of the assistant message
    const allMsgEls = getAllMessageEls();
    const assistantIdx = allMsgEls.indexOf(assistantEl);
    // The user message is the one before it
    const userIdx = assistantIdx - 1;

    if (userIdx < 0) return;

    // Get the user's text from state
    const userText = state.currentMessages[userIdx]?.content || originalUserText;
    if (!userText) return;

    // Remove assistant message (and anything after) from DOM
    for (let i = allMsgEls.length - 1; i >= assistantIdx; i--) {
        allMsgEls[i].remove();
    }
    // Trim currentMessages: keep everything up to (but not including) the assistant
    state.currentMessages.splice(assistantIdx);

    // Re-send the same user message
    sendMessage(userText);
}

function getAllMessageEls() {
    return Array.from(chatMessages.querySelectorAll('.message'));
}

// ═══════════════════════════════════════════════════════════════
//  RENDERING
// ═══════════════════════════════════════════════════════════════
function appendMessage(role, content) {
    const el = document.createElement('div');
    el.className = `message ${role}`;
    const avatar = role === 'user'
        ? (state.user?.email?.[0] || 'U').toUpperCase()
        : 'N';

    el.innerHTML = `
        <div class="message-avatar">${avatar}</div>
        <div class="message-content">
            <div class="message-role">${role === 'user' ? 'You' : 'NexusAI'}</div>
            <div class="message-text">${formatMessage(content)}</div>
            <div class="message-actions">
                ${role === 'user'
                    ? '<button class="msg-action-btn edit-btn"><svg viewBox="0 0 20 20" fill="currentColor" width="12" height="12"><path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"/></svg> Edit</button>'
                    : '<button class="msg-action-btn regen-btn"><svg viewBox="0 0 20 20" fill="currentColor" width="12" height="12"><path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd"/></svg> Regenerate</button>'
                }
            </div>
        </div>
    `;

    // Bind action buttons
    if (role === 'user') {
        el.querySelector('.edit-btn').onclick = () => startEdit(el, content);
    } else {
        el.querySelector('.regen-btn').onclick = () => regenerate(el, content);
    }

    chatMessages.appendChild(el);
    return el;
}

// ═══════════════════════════════════════════════════════════════
//  MARKDOWN FORMATTING
// ═══════════════════════════════════════════════════════════════
function formatMessage(text) {
    if (!text) return '';
    let h = escapeHTML(text);

    // Headers
    h = h.replace(/^### (.*$)/gm, '<h3 class="md-h3">$1</h3>');
    h = h.replace(/^## (.*$)/gm, '<h2 class="md-h2">$1</h2>');

    // Code blocks
    h = h.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) =>
        `<pre><code>${code.trim()}</code></pre>`
    );
    h = h.replace(/`([^`]+)`/g, '<code>$1</code>');

    // Bold
    h = h.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

    // Tables: detect markdown table blocks
    h = h.replace(/((?:^\|.+\|$\n?)+)/gm, (block) => {
        const lines = block.trim().split('\n').filter(l => l.trim());
        if (lines.length < 2) return block;
        const parseRow = (line) =>
            line.replace(/^\|/, '').replace(/\|$/, '').split('|').map(c => c.trim());
        const headers = parseRow(lines[0]);
        let html = '<table><thead><tr>' + headers.map(c => `<th>${c}</th>`).join('') + '</tr></thead><tbody>';
        // Skip separator line (line[1] with dashes)
        for (let i = 2; i < lines.length; i++) {
            const cells = parseRow(lines[i]);
            html += '<tr>' + cells.map(c => `<td>${c}</td>`).join('') + '</tr>';
        }
        return html + '</tbody></table>';
    });

    // Unordered lists
    const outputLines = [];
    let inList = false;
    for (const line of h.split('\n')) {
        const match = line.match(/^(\s*)[-*]\s+(.+)/);
        if (match) {
            if (!inList) { outputLines.push('<ul>'); inList = true; }
            outputLines.push(`<li>${match[2]}</li>`);
        } else {
            if (inList) { outputLines.push('</ul>'); inList = false; }
            outputLines.push(line);
        }
    }
    if (inList) outputLines.push('</ul>');

    return outputLines.join('\n').replace(/\n/g, '<br>');
}

function escapeHTML(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

// ═══════════════════════════════════════════════════════════════
//  UTILITIES
// ═══════════════════════════════════════════════════════════════
function showThinking(container) {
    container.innerHTML = '<div class="inline-thinking"><div class="thinking-dot"></div><div class="thinking-dot"></div><div class="thinking-dot"></div></div>';
}

function scrollToBottom() {
    requestAnimationFrame(() => {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    });
}

// ── Mobile sidebar toggle ───────────────────────────────────────
sidebarToggle.addEventListener('click', () => sidebar.classList.toggle('open'));

// ── Boot ────────────────────────────────────────────────────────
init();
