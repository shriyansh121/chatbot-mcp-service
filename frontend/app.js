/* ═══════════════════════════════════════════════════════════════
   NexusAI — Frontend Application Logic
   Connects to FastAPI backend at /api/auth/* and /api/chat/*
   Features: chat, edit prompt, regenerate, rename/delete sessions
   ═══════════════════════════════════════════════════════════════ */

const API_BASE = window.location.origin;

// ── State ────────────────────────────────────────────────────────
const state = {
    token: localStorage.getItem('nexus_token') || null,
    user: JSON.parse(localStorage.getItem('nexus_user') || 'null'),
    currentSessionId: null,
    sessions: [],
    isLoading: false,
    /** Keeps an ordered list of {role, content, messageId?} for current session */
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
    state.currentMessages = [];
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
        el.innerHTML = `
            <span class="session-title">${escapeHTML(s.title || 'New Conversation')}</span>
            <span class="session-actions">
                <button class="session-action-btn rename" title="Rename">
                    <svg viewBox="0 0 20 20" fill="currentColor"><path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"/></svg>
                </button>
                <button class="session-action-btn delete" title="Delete">
                    <svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z" clip-rule="evenodd"/></svg>
                </button>
            </span>
        `;

        // Title click -> load session
        const titleSpan = el.querySelector('.session-title');
        titleSpan.addEventListener('click', () => loadSession(s.id));

        // Rename
        const renameBtn = el.querySelector('.rename');
        renameBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            startRenameSession(el, s);
        });

        // Delete
        const deleteBtn = el.querySelector('.delete');
        deleteBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            confirmDeleteSession(s.id);
        });

        sessionList.appendChild(el);
    });
}

// ── Rename inline ───────────────────────────────────────────────
function startRenameSession(el, session) {
    const titleSpan = el.querySelector('.session-title');
    const currentTitle = session.title || 'New Conversation';

    // Replace title span with input
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'session-rename-input';
    input.value = currentTitle;
    titleSpan.replaceWith(input);
    input.focus();
    input.select();

    const finishRename = async () => {
        const newTitle = input.value.trim() || currentTitle;
        try {
            await api(`/api/chat/sessions/${session.id}/rename`, {
                method: 'PUT',
                body: JSON.stringify({ title: newTitle }),
            });
            session.title = newTitle;
        } catch (err) {
            console.error('Rename failed:', err);
        }
        loadSessions();
    };

    input.addEventListener('blur', finishRename);
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            input.blur();
        }
        if (e.key === 'Escape') {
            input.value = currentTitle;
            input.blur();
        }
    });
}

// ── Delete with confirmation modal ──────────────────────────────
function confirmDeleteSession(sessionId) {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
        <div class="modal-card">
            <h3>Delete conversation?</h3>
            <p>This will permanently remove this chat and all its messages.</p>
            <div class="modal-buttons">
                <button class="modal-btn-cancel">Cancel</button>
                <button class="modal-btn-delete">Delete</button>
            </div>
        </div>
    `;

    overlay.querySelector('.modal-btn-cancel').addEventListener('click', () => overlay.remove());
    overlay.querySelector('.modal-btn-delete').addEventListener('click', async () => {
        try {
            await api(`/api/chat/sessions/${sessionId}`, { method: 'DELETE' });
            if (state.currentSessionId === sessionId) {
                state.currentSessionId = null;
                state.currentMessages = [];
                clearMessages();
                welcomeScreen.style.display = 'flex';
            }
            state.sessions = state.sessions.filter((s) => s.id !== sessionId);
            renderSessions();
        } catch (err) {
            console.error('Delete failed:', err);
        }
        overlay.remove();
    });
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) overlay.remove();
    });

    document.body.appendChild(overlay);
}

async function loadSession(sessionId) {
    try {
        state.currentSessionId = sessionId;
        renderSessions();
        const session = await api(`/api/chat/sessions/${sessionId}`);
        clearMessages();
        state.currentMessages = [];
        if (session.messages && session.messages.length > 0) {
            welcomeScreen.style.display = 'none';
            session.messages.forEach((m) => {
                state.currentMessages.push({ role: m.role, content: m.content, messageId: m.id });
                appendMessage(m.role, m.content, m.id);
            });
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
        state.currentMessages = [];
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

async function sendMessage(overrideText = null) {
    const text = overrideText || chatInput.value.trim();
    if (!text || state.isLoading) return;

    state.isLoading = true;
    if (!overrideText) {
        chatInput.value = '';
        chatInput.style.height = 'auto';
    }
    btnSend.disabled = true;

    // Hide welcome
    welcomeScreen.style.display = 'none';

    // Show user message
    appendMessage('user', text);
    state.currentMessages.push({ role: 'user', content: text });
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
            loadSessions(); // Refresh session list (will have auto-generated title)
        } else {
            // Refresh session list too (title may have been auto-generated)
            loadSessions();
        }

        // Remove thinking, show response
        removeThinking(thinkingEl);
        appendMessage('assistant', res.message);
        state.currentMessages.push({ role: 'assistant', content: res.message });
    } catch (err) {
        removeThinking(thinkingEl);
        appendMessage('assistant', `⚠️ Error: ${err.message}`);
    } finally {
        state.isLoading = false;
        scrollToBottom();
    }
}

// ═══════════════════════════════════════════════════════════════
//  EDIT & REGENERATE
// ═══════════════════════════════════════════════════════════════
function startEditMessage(msgEl, originalText, msgIndex) {
    const textDiv = msgEl.querySelector('.message-text');
    const actionsDiv = msgEl.querySelector('.message-actions');
    if (actionsDiv) actionsDiv.style.display = 'none';

    const oldHTML = textDiv.innerHTML;
    textDiv.innerHTML = '';

    const textarea = document.createElement('textarea');
    textarea.className = 'edit-area';
    textarea.value = originalText;
    textDiv.appendChild(textarea);

    const btnRow = document.createElement('div');
    btnRow.className = 'edit-buttons';
    const saveBtn = document.createElement('button');
    saveBtn.className = 'edit-btn-save';
    saveBtn.textContent = 'Save & Send';
    const cancelBtn = document.createElement('button');
    cancelBtn.className = 'edit-btn-cancel';
    cancelBtn.textContent = 'Cancel';
    btnRow.appendChild(cancelBtn);
    btnRow.appendChild(saveBtn);
    textDiv.appendChild(btnRow);

    textarea.focus();

    cancelBtn.addEventListener('click', () => {
        textDiv.innerHTML = oldHTML;
        if (actionsDiv) actionsDiv.style.display = '';
    });

    saveBtn.addEventListener('click', async () => {
        const newText = textarea.value.trim();
        if (!newText) return;
        // Remove all messages after this index
        removeMessagesAfterIndex(msgIndex);
        // Update the user message in state
        state.currentMessages.splice(msgIndex);
        // Re-send with edited text
        await sendEditedMessage(newText);
    });
}

async function sendEditedMessage(text) {
    if (!text || state.isLoading) return;

    state.isLoading = true;
    btnSend.disabled = true;

    // Show user message
    appendMessage('user', text);
    state.currentMessages.push({ role: 'user', content: text });
    scrollToBottom();

    const thinkingEl = showThinking();

    try {
        const res = await api('/api/chat/message', {
            method: 'POST',
            body: JSON.stringify({
                message: text,
                session_id: state.currentSessionId,
                edit_mode: true,
            }),
        });

        removeThinking(thinkingEl);
        appendMessage('assistant', res.message);
        state.currentMessages.push({ role: 'assistant', content: res.message });
        loadSessions();
    } catch (err) {
        removeThinking(thinkingEl);
        appendMessage('assistant', `⚠️ Error: ${err.message}`);
    } finally {
        state.isLoading = false;
        scrollToBottom();
    }
}

async function regenerateAfterMessage(msgIndex) {
    // The assistant message at msgIndex — we want to re-generate it.
    // The user message is at msgIndex - 1
    const userMsg = state.currentMessages[msgIndex - 1];
    if (!userMsg || userMsg.role !== 'user') return;

    // Remove the assistant message and everything after
    removeMessagesAfterIndex(msgIndex - 1);
    state.currentMessages.splice(msgIndex);

    // Re-send the same user message
    state.isLoading = true;
    btnSend.disabled = true;
    scrollToBottom();

    const thinkingEl = showThinking();

    try {
        const res = await api('/api/chat/message', {
            method: 'POST',
            body: JSON.stringify({
                message: userMsg.content,
                session_id: state.currentSessionId,
                regenerate: true,
            }),
        });

        removeThinking(thinkingEl);
        appendMessage('assistant', res.message);
        state.currentMessages.push({ role: 'assistant', content: res.message });
        loadSessions();
    } catch (err) {
        removeThinking(thinkingEl);
        appendMessage('assistant', `⚠️ Error: ${err.message}`);
    } finally {
        state.isLoading = false;
        scrollToBottom();
    }
}

function removeMessagesAfterIndex(msgIndex) {
    // Message DOM elements (skip welcome screen)
    const msgEls = Array.from(chatMessages.children).filter(
        (c) => c !== welcomeScreen && c.classList.contains('message')
    );
    for (let i = msgEls.length - 1; i > msgIndex; i--) {
        msgEls[i].remove();
    }
    // Also remove the element AT msgIndex if we want
    if (msgEls[msgIndex]) msgEls[msgIndex].remove();
}

// ═══════════════════════════════════════════════════════════════
//  MESSAGE RENDERING
// ═══════════════════════════════════════════════════════════════
function appendMessage(role, content, messageId) {
    const msgIndex = state.currentMessages.length; // Index BEFORE this push (used for actions)
    const msgEl = document.createElement('div');
    msgEl.className = `message ${role}`;

    const avatarLabel = role === 'user'
        ? (state.user?.full_name?.[0] || state.user?.email?.[0] || 'U').toUpperCase()
        : 'N';

    let actionsHTML = '';
    if (role === 'user') {
        actionsHTML = `
            <div class="message-actions">
                <button class="msg-action-btn edit-btn" title="Edit">
                    <svg viewBox="0 0 20 20" fill="currentColor"><path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"/></svg>
                    Edit
                </button>
            </div>
        `;
    } else {
        actionsHTML = `
            <div class="message-actions">
                <button class="msg-action-btn regenerate-btn" title="Regenerate">
                    <svg viewBox="0 0 20 20" fill="currentColor"><path fill-rule="evenodd" d="M4 2a1 1 0 011 1v2.101a7.002 7.002 0 0111.601 2.566 1 1 0 11-1.885.666A5.002 5.002 0 005.999 7H9a1 1 0 010 2H4a1 1 0 01-1-1V3a1 1 0 011-1zm.008 9.057a1 1 0 011.276.61A5.002 5.002 0 0014.001 13H11a1 1 0 110-2h5a1 1 0 011 1v5a1 1 0 11-2 0v-2.101a7.002 7.002 0 01-11.601-2.566 1 1 0 01.61-1.276z" clip-rule="evenodd"/></svg>
                    Regenerate
                </button>
            </div>
        `;
    }

    msgEl.innerHTML = `
        <div class="message-avatar">${avatarLabel}</div>
        <div class="message-content">
            <div class="message-role">${role === 'user' ? 'You' : 'NexusAI'}</div>
            <div class="message-text">${formatMessage(content)}</div>
            ${actionsHTML}
        </div>
    `;

    // Wire up edit/regenerate buttons
    const editBtn = msgEl.querySelector('.edit-btn');
    if (editBtn) {
        editBtn.addEventListener('click', () => {
            // Find the actual index in currentMessages for this DOM msg
            const allMsgEls = Array.from(chatMessages.children).filter(
                (c) => c !== welcomeScreen && c.classList.contains('message')
            );
            const idx = allMsgEls.indexOf(msgEl);
            startEditMessage(msgEl, content, idx);
        });
    }

    const regenBtn = msgEl.querySelector('.regenerate-btn');
    if (regenBtn) {
        regenBtn.addEventListener('click', () => {
            const allMsgEls = Array.from(chatMessages.children).filter(
                (c) => c !== welcomeScreen && c.classList.contains('message')
            );
            const idx = allMsgEls.indexOf(msgEl);
            regenerateAfterMessage(idx);
        });
    }

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

    // Markdown tables → HTML <table>
    formatted = convertMarkdownTables(formatted);

    // Unordered lists
    formatted = convertUnorderedLists(formatted);

    // Line breaks (after table conversion to avoid breaking table structure)
    formatted = formatted.replace(/\n/g, '<br>');

    return formatted;
}

/**
 * Convert markdown-style tables (|...|) into proper HTML <table> elements.
 */
function convertMarkdownTables(text) {
    // Match table blocks: lines starting with |
    const tableRegex = /((?:^\|.+\|$\n?)+)/gm;
    return text.replace(tableRegex, (tableBlock) => {
        const lines = tableBlock.trim().split('\n').filter((l) => l.trim());
        if (lines.length < 2) return tableBlock; // Need at least header + separator

        // Check if second line is a separator (|---|---|...)
        const secondLine = lines[1].trim();
        const isSep = /^\|[\s\-:|]+\|$/.test(secondLine);

        if (!isSep) return tableBlock; // Not a real table

        const parseRow = (line) =>
            line
                .replace(/^\|/, '')
                .replace(/\|$/, '')
                .split('|')
                .map((cell) => cell.trim());

        const headerCells = parseRow(lines[0]);
        const dataLines = lines.slice(2); // Skip header + separator

        let html = '<table><thead><tr>';
        headerCells.forEach((h) => {
            html += `<th>${h}</th>`;
        });
        html += '</tr></thead><tbody>';

        dataLines.forEach((line) => {
            const cells = parseRow(line);
            html += '<tr>';
            cells.forEach((c) => {
                html += `<td>${c}</td>`;
            });
            html += '</tr>';
        });

        html += '</tbody></table>';
        return html;
    });
}

/**
 * Convert lines starting with - or * into <ul><li> blocks.
 */
function convertUnorderedLists(text) {
    const lines = text.split('\n');
    let result = [];
    let inList = false;

    for (const line of lines) {
        const listMatch = line.match(/^(\s*)[-*]\s+(.+)/);
        if (listMatch) {
            if (!inList) {
                result.push('<ul>');
                inList = true;
            }
            result.push(`<li>${listMatch[2]}</li>`);
        } else {
            if (inList) {
                result.push('</ul>');
                inList = false;
            }
            result.push(line);
        }
    }
    if (inList) result.push('</ul>');
    return result.join('\n');
}

function escapeHTML(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function clearMessages() {
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
