/**
 * Support Knowledge Claw — Admin Dashboard Logic
 * Fetches analytics, logs, and escalations for the admin view.
 */

const API_BASE = '';

// ── Initialize ────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    loadAnalytics();
    loadLogs();
    loadEscalations();
    // Auto-refresh every 30 seconds
    setInterval(() => {
        loadAnalytics();
        loadLogs();
        loadEscalations();
    }, 30000);
});

// ── Load Analytics ────────────────────────────────

async function loadAnalytics() {
    try {
        const res = await fetch(`${API_BASE}/api/analytics/summary`);
        if (!res.ok) throw new Error('Failed to load analytics');
        const data = await res.json();

        document.getElementById('totalQueries').textContent = data.total_queries;
        document.getElementById('totalEscalations').textContent = data.total_escalations;
        document.getElementById('escalationRate').textContent = `${data.escalation_rate}%`;
        document.getElementById('avgConfidence').textContent = `${(data.avg_confidence * 100).toFixed(0)}%`;

        renderBarChart('intentChart', data.intent_distribution, data.total_queries);
        renderBarChart('urgencyChart', data.urgency_distribution, data.total_queries);

    } catch (error) {
        console.error('Analytics error:', error);
    }
}

// ── Load Logs ─────────────────────────────────────

async function loadLogs() {
    const intent = document.getElementById('filterIntent').value;
    const urgency = document.getElementById('filterUrgency').value;
    const status = document.getElementById('filterStatus').value;

    const params = new URLSearchParams();
    params.set('limit', '20');
    if (intent) params.set('intent', intent);
    if (urgency) params.set('urgency', urgency);
    if (status) params.set('status', status);

    try {
        const res = await fetch(`${API_BASE}/api/logs?${params}`);
        if (!res.ok) throw new Error('Failed to load logs');
        const logs = await res.json();
        renderLogsTable(logs);
    } catch (error) {
        document.getElementById('logsTable').innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📝</div>
                <h3>No logs yet</h3>
                <p>Start chatting with the agent to generate support logs.</p>
            </div>
        `;
    }
}

// ── Load Escalations ──────────────────────────────

async function loadEscalations() {
    try {
        const res = await fetch(`${API_BASE}/api/escalations?limit=20`);
        if (!res.ok) throw new Error('Failed to load escalations');
        const escalations = await res.json();
        renderEscalationsTable(escalations);
    } catch (error) {
        document.getElementById('escalationsTable').innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">🚨</div>
                <h3>No escalations</h3>
                <p>Low-confidence or critical queries will appear here.</p>
            </div>
        `;
    }
}

// ── Render Bar Chart ──────────────────────────────

function renderBarChart(containerId, distribution, total) {
    const container = document.getElementById(containerId);
    if (!distribution || Object.keys(distribution).length === 0) {
        container.innerHTML = '<div class="empty-state"><p>No data yet</p></div>';
        return;
    }

    const maxVal = Math.max(...Object.values(distribution));

    const html = Object.entries(distribution)
        .sort((a, b) => b[1] - a[1])
        .map(([label, count]) => {
            const pct = maxVal > 0 ? (count / maxVal) * 100 : 0;
            return `
                <div class="bar-item">
                    <span class="bar-label">${escapeHtml(label.replace(/_/g, ' '))}</span>
                    <div class="bar-track">
                        <div class="bar-fill" style="width: ${pct}%"></div>
                    </div>
                    <span class="bar-count">${count}</span>
                </div>
            `;
        }).join('');

    container.innerHTML = html;
}

// ── Render Logs Table ─────────────────────────────

function renderLogsTable(logs) {
    const container = document.getElementById('logsTable');

    if (!logs || logs.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">📝</div>
                <h3>No logs found</h3>
                <p>Try changing your filters or start chatting.</p>
            </div>
        `;
        return;
    }

    const rows = logs.map(log => `
        <tr>
            <td>#${log.id}</td>
            <td class="truncate" title="${escapeHtml(log.query)}">${escapeHtml(log.query)}</td>
            <td><span class="meta-badge badge-intent">${escapeHtml(log.intent)}</span></td>
            <td><span class="meta-badge badge-urgency-${log.urgency}">${escapeHtml(log.urgency)}</span></td>
            <td>${(log.confidence * 100).toFixed(0)}%</td>
            <td><span class="meta-badge badge-status-${escapeHtml(log.status)}">${escapeHtml(log.status)}</span></td>
            <td>${formatDate(log.created_at)}</td>
        </tr>
    `).join('');

    container.innerHTML = `
        <table class="data-table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Query</th>
                    <th>Intent</th>
                    <th>Urgency</th>
                    <th>Conf.</th>
                    <th>Status</th>
                    <th>Time</th>
                </tr>
            </thead>
            <tbody>${rows}</tbody>
        </table>
    `;
}

// ── Render Escalations Table ──────────────────────

function renderEscalationsTable(escalations) {
    const container = document.getElementById('escalationsTable');

    if (!escalations || escalations.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">✅</div>
                <h3>No escalations</h3>
                <p>All queries resolved autonomously!</p>
            </div>
        `;
        return;
    }

    const rows = escalations.map(e => `
        <tr>
            <td>#${e.id}</td>
            <td class="truncate" title="${escapeHtml(e.query)}">${escapeHtml(e.query)}</td>
            <td><span class="meta-badge badge-urgency-${e.urgency}">${escapeHtml(e.escalation_priority || e.urgency)}</span></td>
            <td>${escapeHtml(e.assigned_team || '—')}</td>
            <td><span class="meta-badge badge-status-${escapeHtml(e.status)}">${escapeHtml(e.status)}</span></td>
            <td class="truncate" title="${escapeHtml(e.escalation_reason)}">${escapeHtml(e.escalation_reason || '—')}</td>
            <td>${formatDate(e.created_at)}</td>
        </tr>
    `).join('');

    container.innerHTML = `
        <table class="data-table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Query</th>
                    <th>Priority</th>
                    <th>Team</th>
                    <th>Status</th>
                    <th>Reason</th>
                    <th>Time</th>
                </tr>
            </thead>
            <tbody>${rows}</tbody>
        </table>
    `;
}

// ── Utilities ─────────────────────────────────────

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatDate(dateStr) {
    if (!dateStr) return '—';
    try {
        const d = new Date(dateStr);
        return d.toLocaleString('en-IN', {
            day: '2-digit', month: 'short',
            hour: '2-digit', minute: '2-digit',
        });
    } catch {
        return dateStr;
    }
}
