const $ = (sel) => document.querySelector(sel);
const API = '/api';

let currentTaskId = null;
let pollTimer = null;

// --- Init ---
document.addEventListener('DOMContentLoaded', () => {
    loadHistory();
    loadStorage();
    $('#submit-form').addEventListener('submit', handleSubmit);
    $('#cleanup-btn').addEventListener('click', handleCleanup);
    $('#toggle-transcript').addEventListener('click', toggleTranscript);
});

// --- Submit ---
async function handleSubmit(e) {
    e.preventDefault();
    const url = $('#url-input').value.trim();
    if (!url) {
        $('#url-input').classList.add('invalid');
        return;
    }
    $('#url-input').classList.remove('invalid');

    const btn = $('#submit-btn');
    btn.disabled = true;
    btn.textContent = '提交中...';

    try {
        const resp = await fetch(`${API}/summarize`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                url,
                language: $('#language-select').value,
                llm_provider: $('#provider-select').value,
            }),
        });

        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || '请求失败');
        }

        const data = await resp.json();
        currentTaskId = data.task_id;
        showResultSection();
        startPolling(currentTaskId);
    } catch (err) {
        showError(err.message);
    } finally {
        btn.disabled = false;
        btn.textContent = '提交';
    }
}

// --- Polling ---
function startPolling(taskId) {
    stopPolling();
    pollTimer = setInterval(() => pollTask(taskId), 2000);
    pollTask(taskId);
}

function stopPolling() {
    if (pollTimer) {
        clearInterval(pollTimer);
        pollTimer = null;
    }
}

async function pollTask(taskId) {
    try {
        const resp = await fetch(`${API}/tasks/${taskId}`);
        if (!resp.ok) throw new Error('查询失败');
        const task = await resp.json();
        updateResult(task);

        if (task.status === 'done' || task.status === 'failed') {
            stopPolling();
            loadHistory();
            loadStorage();
        }
    } catch (err) {
        stopPolling();
        showError(err.message);
    }
}

// --- Result display ---
function showResultSection() {
    $('#result-section').classList.remove('hidden');
    $('#result-content').classList.add('hidden');
    $('#result-error').classList.add('hidden');
    $('#toggle-transcript').classList.add('hidden');
    $('#result-transcript').classList.add('hidden');
}

function updateResult(task) {
    const statusMap = {
        pending: '等待中',
        downloading: '下载中',
        transcribing: '转录中',
        summarizing: '总结中',
        done: '完成',
        failed: '失败',
    };

    const progressMap = {
        pending: 5,
        downloading: 25,
        transcribing: 50,
        summarizing: 75,
        done: 100,
        failed: 100,
    };

    $('#status-text').textContent = statusMap[task.status] || task.status;
    const fill = $('#progress-fill');
    fill.style.width = progressMap[task.status] + '%';
    fill.className = task.status === 'done' ? 'done' : task.status === 'failed' ? 'failed' : '';

    if (task.status === 'done') {
        $('#result-content').classList.remove('hidden');
        $('#result-error').classList.add('hidden');

        const title = task.metadata?.title || '未知标题';
        $('#result-title').textContent = title;

        const meta = [];
        if (task.metadata?.duration) meta.push(`时长: ${formatDuration(task.metadata.duration)}`);
        if (task.platform) meta.push(`平台: ${task.platform}`);
        $('#result-meta').textContent = meta.join(' | ');

        $('#result-summary').textContent = task.summary || '';

        if (task.transcript) {
            $('#result-transcript').textContent = task.transcript;
            $('#toggle-transcript').classList.remove('hidden');
        }
    } else if (task.status === 'failed') {
        $('#result-content').classList.add('hidden');
        $('#result-error').classList.remove('hidden');
        $('#result-error').textContent = task.error || '未知错误';
    }
}

function toggleTranscript() {
    const el = $('#result-transcript');
    const btn = $('#toggle-transcript');
    if (el.classList.contains('hidden')) {
        el.classList.remove('hidden');
        btn.textContent = '收起转录原文';
    } else {
        el.classList.add('hidden');
        btn.textContent = '展开转录原文';
    }
}

function showError(msg) {
    showResultSection();
    $('#result-content').classList.add('hidden');
    $('#result-error').classList.remove('hidden');
    $('#result-error').textContent = msg;
    $('#status-text').textContent = '错误';
    const fill = $('#progress-fill');
    fill.className = 'failed';
    fill.style.width = '100%';
}

// --- History ---
async function loadHistory() {
    try {
        const resp = await fetch(`${API}/tasks`);
        if (!resp.ok) return;
        const data = await resp.json();
        renderHistory(data.tasks);
    } catch (_) {}
}

function renderHistory(tasks) {
    const body = $('#history-body');
    const empty = $('#history-empty');

    if (!tasks.length) {
        body.innerHTML = '';
        empty.classList.remove('hidden');
        return;
    }

    empty.classList.add('hidden');

    // Sort by created_at descending
    tasks.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));

    body.innerHTML = tasks.map(t => {
        const title = t.metadata?.title || truncateUrl(t.url);
        const time = formatTime(t.created_at);
        const statusLabel = {
            pending: '等待中',
            downloading: '下载中',
            transcribing: '转录中',
            summarizing: '总结中',
            done: '完成',
            failed: '失败',
        }[t.status] || t.status;

        return `<tr>
            <td>${time}</td>
            <td>${escapeHtml(title)}</td>
            <td><span class="status-badge status-${t.status}">${statusLabel}</span></td>
            <td><button class="view-btn" data-id="${t.task_id}">查看</button></td>
        </tr>`;
    }).join('');

    body.querySelectorAll('.view-btn').forEach(btn => {
        btn.addEventListener('click', () => viewTask(btn.dataset.id));
    });
}

async function viewTask(taskId) {
    try {
        const resp = await fetch(`${API}/tasks/${taskId}`);
        if (!resp.ok) return;
        const task = await resp.json();
        currentTaskId = taskId;
        showResultSection();
        updateResult(task);
        stopPolling();
        if (task.status !== 'done' && task.status !== 'failed') {
            startPolling(taskId);
        }
        $('#result-section').scrollIntoView({ behavior: 'smooth' });
    } catch (_) {}
}

// --- Storage ---
async function loadStorage() {
    try {
        const resp = await fetch(`${API}/storage`);
        if (!resp.ok) return;
        const data = await resp.json();
        const total = data.db_size_bytes + data.cache_size_bytes;
        $('#storage-info').textContent = `${data.task_count} 个任务 | ${formatBytes(total)}`;
    } catch (_) {}
}

async function handleCleanup() {
    if (!confirm('确定要清理所有存储数据吗？此操作不可恢复。')) return;

    try {
        const resp = await fetch(`${API}/storage`, { method: 'DELETE' });
        if (!resp.ok) throw new Error('清理失败');
        const data = await resp.json();
        loadStorage();
        loadHistory();
        alert(`清理完成：删除 ${data.deleted_tasks} 个任务，释放 ${formatBytes(data.freed_bytes)}`);
    } catch (err) {
        alert(err.message);
    }
}

// --- Helpers ---
function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const units = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return (bytes / Math.pow(k, i)).toFixed(1) + ' ' + units[i];
}

function formatDuration(seconds) {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return m > 0 ? `${m}分${s}秒` : `${s}秒`;
}

function formatTime(iso) {
    const d = new Date(iso);
    const pad = (n) => String(n).padStart(2, '0');
    return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function truncateUrl(url) {
    try {
        const u = new URL(url);
        return u.hostname + u.pathname.slice(0, 20);
    } catch {
        return url.slice(0, 30);
    }
}

function escapeHtml(str) {
    const el = document.createElement('span');
    el.textContent = str;
    return el.innerHTML;
}
