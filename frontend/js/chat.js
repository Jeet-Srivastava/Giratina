/**
 * Support Knowledge Claw — Chat Interface Logic
 * Handles message sending, response rendering, and agent step display.
 */

// Use relative URLs (same-origin) — eliminates all CORS issues
const API_BASE = '';

let isProcessing = false;

// ── Send Message ──────────────────────────────────

async function sendMessage() {
    const input = document.getElementById('chatInput');
    const query = input.value.trim();
    if (!query || isProcessing) return;

    // Hide welcome screen
    const welcome = document.getElementById('welcomeScreen');
    if (welcome) welcome.remove();

    // Show user message
    appendMessage('user', query);
    input.value = '';
    autoResize(input);
    setProcessing(true);

    // Show thinking indicator
    const thinkingEl = showThinking();

    try {
        const response = await fetch(`${API_BASE}/api/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query }),
        });

        if (!response.ok) {
            const err = await response.json().catch(() => ({}));
            throw new Error(err.detail || `Server error (${response.status})`);
        }

        const data = await response.json();
        removeThinking(thinkingEl);
        appendAgentResponse(data);

    } catch (error) {
        removeThinking(thinkingEl);
        appendMessage('agent', `❌ Error: ${error.message}\n\nPlease check that the server is running and your API key is configured.`);
    } finally {
        setProcessing(false);
    }
}

// ── Example Query ─────────────────────────────────

function sendExample(el) {
    const input = document.getElementById('chatInput');
    // Remove the emoji prefix
    input.value = el.textContent.replace(/^[^\w]*/, '').trim();
    sendMessage();
}

// ── Append Messages ───────────────────────────────

function appendMessage(role, text) {
    const container = document.getElementById('chatMessages');
    const avatar = role === 'user' ? '👤' : '🦀';

    const messageHtml = `
        <div class="message ${role}">
            <div class="message-avatar">${avatar}</div>
            <div class="message-content">
                <div class="message-text">${escapeHtml(text)}</div>
            </div>
        </div>
    `;
    container.insertAdjacentHTML('beforeend', messageHtml);
    container.scrollTop = container.scrollHeight;
}

function appendAgentResponse(data) {
    const container = document.getElementById('chatMessages');

    // Format the response text with basic markdown-like formatting
    let responseText = data.response || 'No response generated.';
    responseText = formatResponse(responseText);

    // Build metadata badges
    const urgencyClass = `badge-urgency-${data.urgency}`;
    const statusBadge = data.needs_escalation
        ? '<span class="meta-badge badge-escalated">🚨 Escalated</span>'
        : '<span class="meta-badge badge-resolved">✅ Resolved</span>';

    // Build agent steps
    let stepsHtml = '';
    if (data.agent_steps && data.agent_steps.length > 0) {
        const stepItems = data.agent_steps.map(s => `
            <div class="step-item">
                <div class="step-icon">✓</div>
                <span>${escapeHtml(s.step)}: ${escapeHtml(s.result)}</span>
                ${s.duration_ms ? `<span class="step-duration">${s.duration_ms}ms</span>` : ''}
            </div>
        `).join('');

        stepsHtml = `
            <div class="agent-steps">
                <button class="steps-toggle" onclick="toggleSteps(this)">
                    ▶ Show agent reasoning (${data.agent_steps.length} steps)
                </button>
                <div class="steps-list" style="display:none;">
                    ${stepItems}
                </div>
            </div>
        `;
    }

    // Build escalation box
    let escalationHtml = '';
    if (data.needs_escalation && data.escalation) {
        const e = data.escalation;
        escalationHtml = `
            <div class="escalation-box">
                <div class="escalation-title">🚨 Escalation Created — ${escapeHtml(e.priority)}</div>
                <div class="escalation-detail"><strong>Team:</strong> ${escapeHtml(e.assigned_team)}</div>
                <div class="escalation-detail"><strong>Summary:</strong> ${escapeHtml(e.summary)}</div>
                <div class="escalation-detail"><strong>Action:</strong> ${escapeHtml(e.recommended_action)}</div>
                ${e.sla ? `<div class="escalation-detail"><strong>SLA:</strong> ${escapeHtml(e.sla)}</div>` : ''}
            </div>
        `;
    }

    // Build sources
    let sourcesHtml = '';
    if (data.sources && data.sources.length > 0) {
        const tags = data.sources.map(s => `<span class="source-tag">📄 ${escapeHtml(s)}</span>`).join('');
        sourcesHtml = `<div class="sources">${tags}</div>`;
    }

    const messageHtml = `
        <div class="message agent">
            <div class="message-avatar">🦀</div>
            <div class="message-content">
                <div class="message-text">${responseText}</div>
                <div class="agent-meta">
                    <div class="meta-row">
                        <span class="meta-badge badge-intent">📋 ${escapeHtml(data.intent)}</span>
                        <span class="meta-badge ${urgencyClass}">⚡ ${escapeHtml(data.urgency)}</span>
                        <span class="meta-badge badge-confidence">🎯 ${(data.confidence * 100).toFixed(0)}%</span>
                        ${statusBadge}
                    </div>
                    ${sourcesHtml}
                    ${stepsHtml}
                </div>
                ${escalationHtml}
            </div>
        </div>
    `;

    container.insertAdjacentHTML('beforeend', messageHtml);
    container.scrollTop = container.scrollHeight;
}

// ── Thinking Indicator ────────────────────────────

function showThinking() {
    const container = document.getElementById('chatMessages');
    const el = document.createElement('div');
    el.className = 'message agent';
    el.innerHTML = `
        <div class="message-avatar">🦀</div>
        <div class="message-content">
            <div class="thinking">
                <div class="thinking-dots">
                    <span></span><span></span><span></span>
                </div>
                Analyzing your query...
            </div>
        </div>
    `;
    container.appendChild(el);
    container.scrollTop = container.scrollHeight;
    return el;
}

function removeThinking(el) {
    if (el && el.parentNode) el.parentNode.removeChild(el);
}

// ── Toggle Steps ──────────────────────────────────

function toggleSteps(btn) {
    const list = btn.nextElementSibling;
    const isHidden = list.style.display === 'none';
    list.style.display = isHidden ? 'flex' : 'none';
    btn.textContent = isHidden
        ? `▼ Hide agent reasoning (${list.children.length} steps)`
        : `▶ Show agent reasoning (${list.children.length} steps)`;
}

// ── Utilities ─────────────────────────────────────

function setProcessing(state) {
    isProcessing = state;
    document.getElementById('sendBtn').disabled = state;
    document.getElementById('chatInput').disabled = state;
}

function handleKeydown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

function autoResize(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 120) + 'px';
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatResponse(text) {
    // Convert **bold** to <strong>
    text = escapeHtml(text);
    text = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    // Convert numbered lists
    text = text.replace(/^(\d+)\.\s/gm, '<br>$1. ');
    // Convert line breaks
    text = text.replace(/\n/g, '<br>');
    return text;
}
