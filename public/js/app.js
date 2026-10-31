'use strict';

const state = { user: null, panel: 'chat', chatHistory: [], evaluation: null, knowledgeQuery: '', policyQuery: 'payment portal failed', loading: false };
const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];

function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[char]));
}
function cleanCredentialText(text) {
  return String(text || '')
    .replace(/((?:my\s+)?(?:password|passcode|otp|one[- ]time password|verification code|security code|cvv|pin)\s*(?:is|=|:|equals|was)\s*)[^\s,;.!?]{3,}/ig, '$1[REDACTED]')
    .replace(/((?:remember|save|store|memorize)\b.{0,50}\b(?:password|passcode|otp|one[- ]time password|verification code|security code|cvv|pin)\b)(?:\s*(?:is|=|:|of)?\s*[^\s,;.!?]{4,})?/ig, '$1 [REDACTED]')
    .replace(/((?:otp|passcode|verification code|security code)\b.{0,30}\b)\d{4,8}\b/ig, '$1[REDACTED]');
}
function markdownSafe(input) {
  let html = esc(input);
  html = html.replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1 ↗</a>');
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
  const blocks = html.split(/\n\s*\n/).map(block => {
    const lines = block.split('\n');
    if (lines.every(line => /^\s*[-•]\s+/.test(line))) {
      return '<ul>' + lines.map(line => '<li>' + line.replace(/^\s*[-•]\s+/, '') + '</li>').join('') + '</ul>';
    }
    return '<p>' + lines.join('<br>') + '</p>';
  });
  return blocks.join('');
}
async function api(url, options = {}) {
  const headers = { ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...(options.headers || {}) };
  const response = await fetch(url, { credentials: 'same-origin', ...options, headers });
  let payload;
  try { payload = await response.json(); } catch { payload = { ok: false, error: `Server returned ${response.status}.` }; }
  if (!response.ok || payload.ok === false) throw new Error(payload.error || payload.message || 'The request could not be completed.');
  return payload;
}
function toast(message, duration = 3200) {
  const el = $('#toast');
  el.textContent = message;
  el.classList.add('show');
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => el.classList.remove('show'), duration);
}
function dateText(value) {
  if (!value) return '—';
  try { return new Date(value).toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' }); }
  catch { return String(value); }
}
function money(value) {
  const number = Number(value);
  return Number.isFinite(number) ? '₹' + number.toLocaleString('en-IN') : '—';
}
function chip(status) {
  const value = String(status || 'unknown');
  let cls = 'neutral';
  if (/pending|open/i.test(value)) cls = 'pending';
  if (/reject|denied|fail/i.test(value)) cls = 'rejected';
  if (/approve|paid|success|allowed|closed/i.test(value)) cls = '';
  return `<span class="status-chip ${cls}">${esc(value.replaceAll('_', ' '))}</span>`;
}
function empty(message) { return `<div class="empty-state">${esc(message)}</div>`; }
function dataTable(headers, rows, minWidth = 620) {
  if (!rows?.length) return empty('No records to display yet.');
  return `<div class="data-table-wrap"><table class="data-table" style="min-width:${minWidth}px"><thead><tr>${headers.map(h => `<th>${esc(h.label)}</th>`).join('')}</tr></thead><tbody>${rows.map(row => '<tr>' + headers.map(h => `<td class="${h.className || ''}">${h.render ? h.render(row[h.key], row) : esc(row[h.key] ?? '—')}</td>`).join('') + '</tr>').join('')}</tbody></table></div>`;
}
function setUser(user) {
  state.user = user || null;
  $('#loginOpen').classList.toggle('hidden', !!user);
  $('#logoutButton').classList.toggle('hidden', !user);
  $('#workspace').classList.toggle('hidden', !user);
  if (user) {
    $('#userName').textContent = user.display_name || user.username;
    $('#userRole').textContent = user.role === 'approver' ? 'Human approver' : `Student · ${user.student_id || ''}`;
    $('#userInitials').textContent = (user.display_name || user.username || 'U').split(/\s+/).slice(0, 2).map(x => x[0]).join('').toUpperCase();
    $('#chatUserName').textContent = (user.display_name || 'student').split(' ')[0];
    $('#chatLoginPrompt').classList.toggle('hidden', user.role === 'student');
    $('#chatAuthenticated').classList.toggle('hidden', user.role !== 'student');
    if (user.role === 'approver') {
      $('#chatLoginPrompt').innerHTML = '<h3>Assignment 2 requires a signed-in student account</h3><p>Please sign out and use one of the fictional student demo accounts to demonstrate fee, scholarship, policy, memory and support-request tools.</p>';
    }
    $('#workspaceTitle').textContent = 'Your Student Support';
    $('#workspaceSubtitle').textContent = 'Review your fictional demo records, saved preferences, policy evidence and agent traces.';
    state.panel = 'chat';
    buildTabs();
    renderPanel(state.panel).catch(err => toast(err.message));
  } else {
    $('#workspace').classList.add('hidden');
    $('#chatLoginPrompt').classList.remove('hidden');
    $('#chatAuthenticated').classList.add('hidden');
    $('#chatLoginPrompt').innerHTML = '<h3>Your campus assistant</h3><p>Sign in with a demo student account to ask questions and access your own fictional records.</p><button class="btn btn-primary btn-full" data-open-login>Sign in to chat</button><div class="chat-demo-hint">Local accounts are provisioned during first-time setup. See README.md.</div>';
    state.chatHistory = [];
    $('#chatMessages').innerHTML = '<div class="chat-message assistant"><p>Welcome! I can help with AIDTM public information and general study questions. What would you like to know?</p></div>';
  }
}

function buildTabs() {
  // Assignment 2 workspace: keep the interface focused on the agent, its memory,
  // the single student-policy retriever, and the run-level evaluation evidence.
  const tabs = [
    { key: 'chat', label: 'Student Chat' },
    { key: 'records', label: 'My Records & Memory' },
    { key: 'policy', label: 'Student Policy' },
    { key: 'traces', label: 'Agent Traces' },
    { key: 'evaluation', label: 'Evaluation' },
  ];
  $('#workspaceTabs').innerHTML = tabs.map(item => `<button class="workspace-tab ${state.panel === item.key ? 'active' : ''}" data-panel="${item.key}">${esc(item.label)}</button>`).join('');
}
function showWorkspace(panel) {
  if (!state.user) { openLogin(); return; }
  state.panel = panel;
  buildTabs();
  renderPanel(panel).catch(err => toast(err.message));
  $('#workspace').scrollIntoView({ behavior: 'smooth', block: 'start' });
}
async function renderPanel(panel) {
  const root = $('#workspaceContent');
  root.innerHTML = '<div class="loading-state"><span class="spinner"></span> Loading securely…</div>';
  if (panel === 'chat') {
    root.innerHTML = `<div class="content-card"><div class="content-row"><div><h3>Ask the AIDTM assistant</h3><p>Use the assistant at the top of this page to ask about AIDTM, your own demo records or study topics. Private lookups use your signed-in identity. Approvals are available only to the approver role.</p></div><button class="btn btn-primary" id="openChatFromPanel">Open chat ↗</button></div><div class="result-banner warning">Passwords and OTPs are blocked from model calls and redacted from persistent traces. All student records are fictional coursework data.</div></div>`;
    return;
  }
  if (panel === 'dashboard' || panel === 'records') {
    const data = await api('/api/dashboard');
    root.innerHTML = renderRecords(data);
    return;
  }
  if (panel === 'traces') {
    const data = await api('/api/traces');
    root.innerHTML = renderTraces(data.traces || []);
    return;
  }
  if (panel === 'policy') {
    const data = await api(`/api/policy?q=${encodeURIComponent(state.policyQuery)}`);
    root.innerHTML = renderPolicy(data.chunks || [], data.result || null);
    return;
  }
  if (panel === 'evaluation') {
    root.innerHTML = renderEvaluationIntro(state.evaluation);
    return;
  }
  root.innerHTML = empty('Select a workspace section.');
}
function renderPolicy(chunks, result) {
  const results = result?.results || [];
  const content = result
    ? (results.length ? `<div class="link-card-grid">${results.map(item => `<article class="link-card"><strong>${esc(item.heading || 'Policy section')}</strong><p>${esc(item.text || '')}</p><p class="small-muted">Chunk: ${esc(item.chunk_id || '—')} · relevance score: ${esc(item.score ?? '—')}</p></article>`).join('')}</div>` : empty('No matching section was found. The agent should state that the supplied policy does not contain enough information rather than guess.'))
    : `<div class="link-card-grid">${chunks.map(item => `<article class="link-card"><strong>${esc(item.heading || 'Policy section')}</strong><p>${esc(String(item.text || '').slice(0, 230))}${String(item.text || '').length > 230 ? '…' : ''}</p><p class="small-muted">Chunk: ${esc(item.chunk_id || '—')}</p></article>`).join('')}</div>`;
  return `<div class="content-card"><div class="section-title-row"><h3>Student policy retrieval</h3><span class="badge-note">One bundled document · targeted chunks</span></div><p>The retriever searches <code>data/sample_college_policy.md</code> and returns only the section(s) relevant to your query. This is fictional coursework policy, not official AIDTM policy.</p><form class="inline-form" id="policySearch"><label>Search the student policy<input name="query" value="${esc(state.policyQuery)}" placeholder="e.g. payment portal failure" required></label><button class="btn btn-primary" type="submit">Retrieve relevant sections →</button></form>${result ? `<div class="result-banner">${esc(result.message || 'Search complete.')}</div>` : ''}<div style="margin-top:18px">${content}</div></div>`;
}

function renderRecords(data) {
  const fee = data.fee || {};
  const scholarship = data.scholarship || {};
  const memoryRows = data.memories || [];
  const ticketRows = data.tickets || [];
  const changeRows = data.requests || [];
  return `<div class="metric-grid"><article class="metric-card"><span>Total fee · sample</span><strong>${money(fee.total_fee)}</strong><small>Sample due date: ${esc(fee.due_date || '—')}</small></article><article class="metric-card"><span>Paid · sample</span><strong>${money(fee.paid_fee)}</strong><small>Fictional demo record</small></article><article class="metric-card"><span>Pending · sample</span><strong>${money(fee.pending_fee)}</strong><small>Status: ${esc(fee.fee_status || '—')}</small></article><article class="metric-card"><span>Scholarship</span><strong style="font-size:18px">${esc(scholarship.scholarship_status || 'Not available')}</strong><small>Fictional demo status</small></article></div>
  <div class="content-card"><h3>My academic record</h3><p><b>Programme:</b> ${esc(fee.programme || '—')} &nbsp; <b>Student ID:</b> ${esc(data.user?.student_id || '—')}</p><div class="result-banner warning">These figures are fictional coursework data, not official AIDTM finance or scholarship information.</div></div>
  <div class="content-card"><h3>Consent-based preferences</h3><p>Preferences can be stored only when you enable consent and explicitly choose a non-sensitive preference. Passwords, OTPs and account details must never be saved.</p>
  <form id="memoryForm" class="inline-form"><label>Preference type<select name="key"><option value="programme">Preferred programme</option><option value="preferred_language">Preferred language</option><option value="answer_style">Answer style</option></select></label><label>Preference value<input name="value" placeholder="e.g. PGDM in Big Data Analytics" maxlength="120" required></label><label style="flex-direction:row;align-items:center;padding-bottom:10px"><input type="checkbox" name="consent" required style="min-width:0;accent-color:var(--magenta)"> I consent to save this preference</label><button type="submit" class="btn btn-primary">Save preference</button></form>
  <div style="margin-top:18px">${memoryRows.length ? dataTable([{key:'memory_key',label:'Preference',render:v=>esc(String(v).replaceAll('_',' '))},{key:'memory_value',label:'Saved value'},{key:'updated_at',label:'Updated',render:v=>esc(dateText(v))},{key:'memory_id',label:'Action',render:(v)=>`<button class="section-action" data-delete-memory="${Number(v)}">Delete</button>`}],memoryRows) : empty('No saved preferences yet.')}</div></div>
  <div class="content-card"><h3>My programme-change requests</h3><p>Course-change requests are recorded as requests; the student programme is not changed directly by the chatbot.</p>${dataTable([{key:'request_id',label:'Request ID'},{key:'requested_value',label:'Requested programme',className:'small-cell'},{key:'status',label:'Status',render:v=>chip(v)},{key:'created_at',label:'Created',render:v=>esc(dateText(v))}],changeRows)}</div>
  <div class="content-card"><h3>My local demo support tickets</h3>${dataTable([{key:'ticket_id',label:'Ticket ID'},{key:'category',label:'Category'},{key:'description',label:'Description',className:'small-cell'},{key:'status',label:'Status',render:v=>chip(v)},{key:'created_at',label:'Created',render:v=>esc(dateText(v))}],ticketRows)}</div>`;
}
function renderTraces(traces) {
  const headers = [
    {key:'created_at',label:'Time',render:v=>esc(dateText(v))},
    {key:'trace_id',label:'Trace ID'},
    {key:'question',label:'Question',className:'small-cell'},
    {key:'tools_used',label:'Tools',className:'small-cell'},
    {key:'tool_success',label:'Tool success',render:v=>chip(v ? 'success' : 'partial / failed')},
    {key:'latency_ms',label:'Latency',render:v=>`${Number(v||0).toFixed(1)} ms`},
    {key:'input_tokens',label:'Input tokens',render:v=>v == null ? 'N/A' : esc(v)},
    {key:'output_tokens',label:'Output tokens',render:v=>v == null ? 'N/A' : esc(v)},
    {key:'retrieved_evidence',label:'Retrieved evidence',className:'small-cell'},
    {key:'answer',label:'Agent answer',className:'small-cell'},
    {key:'mode',label:'Mode'},
  ];
  return `<div class="content-card"><div class="section-title-row"><h3>Per-question agent traces</h3><button class="section-action" id="downloadTraces">Download CSV</button></div><p>Each run stores the question, answer, selected tool(s), tool outcome, latency, retrieved policy/memory evidence and model token usage when returned by the API.</p>${dataTable(headers,traces.map(x=>({...x, retrieved_evidence:String(x.retrieved_evidence||'').replaceAll('\n',' · ')})),1350)}<p class="small-muted">Offline mode has no API token usage to report; the fields show N/A rather than fabricated counts. Live Groq responses may include API-reported usage.</p></div>`;
}
function renderEvaluationIntro(report) {
  if (!report) return `<div class="content-card"><div class="section-title-row"><h3>Assignment 2 evaluation</h3><span class="badge-note">Student-support functional suite</span></div><p>Run the defined test questions for fee and scholarship tools, policy retrieval, support requests, course-change requests, persistent memory, sensitive input handling, missing policy information, general study support and tool-error handling.</p><div class="result-banner warning">Evaluation uses an isolated temporary database and deterministic offline mode. API token usage is N/A in this run; live chat traces record input/output tokens when the model API supplies them.</div><button class="btn btn-primary" id="runEvaluation">Run Assignment 2 evaluation <span>→</span></button></div>`;
  const summary = report.summary || {};
  const rows = report.rows || [];
  return `<div class="content-card"><div class="section-title-row"><h3>Assignment 2 evaluation results</h3><button class="section-action" id="runEvaluation">Run again</button></div><div class="evaluation-summary"><article class="metric-card"><span>Task success</span><strong>${Number(summary.passed||0)}/${Number(summary.total||0)}</strong><small>${Math.round(Number(summary.success_rate||0)*100)}% functional checks passed</small></article><article class="metric-card"><span>Mean latency</span><strong>${summary.mean_latency_ms == null ? 'N/A' : `${Number(summary.mean_latency_ms).toFixed(2)} ms`}</strong><small>Local offline run; machine-dependent</small></article><article class="metric-card"><span>Trace records</span><strong>${Number(summary.trace_count||0)}</strong><small>Expected one trace per test run</small></article><article class="metric-card"><span>Runs with API token data</span><strong>${Number(summary.token_runs||0)}/${Number(summary.total||0)}</strong><small>Offline run reports N/A</small></article></div><div style="margin-top:21px"><h3>Test questions and outcomes</h3>${dataTable([{key:'test_id',label:'Test'},{key:'question',label:'Question',className:'small-cell'},{key:'passed',label:'Result',render:v=>chip(v?'PASS':'FAIL')},{key:'tools_used',label:'Tools',className:'small-cell'},{key:'tool_success',label:'Tool result',render:v=>chip(v?'success':'failed / n.a.')},{key:'latency_ms',label:'Latency',render:v=>v==null?'—':`${Number(v).toFixed(2)} ms`},{key:'input_tokens',label:'Input tokens',render:v=>v==null?'N/A':v},{key:'output_tokens',label:'Output tokens',render:v=>v==null?'N/A':v},{key:'retrieved_evidence',label:'Evidence',className:'small-cell'},{key:'answer',label:'Answer',className:'small-cell'}],rows.map(r=>({...r,tools_used:Array.isArray(r.tools_used)?r.tools_used.join(', '):r.tools_used,retrieved_evidence:Array.isArray(r.retrieved_evidence)?r.retrieved_evidence.join(' · '):r.retrieved_evidence})),1450)}</div><div class="result-banner warning">${esc(report.note || 'Functional checks do not replace human review. Token values are shown only when supplied by the model API.')}</div><button class="section-action" id="downloadEvaluation">Download Assignment 2 evaluation CSV</button></div>`;
}
function buildCsv(rows) {
  if (!rows?.length) return '';
  const headers = [...new Set(rows.flatMap(row => Object.keys(row)))];
  const cell = v => '"' + String(v ?? '').replace(/"/g, '""').replace(/\r?\n/g, ' ') + '"';
  return [headers.map(cell).join(','), ...rows.map(row => headers.map(h => cell(row[h])).join(','))].join('\r\n');
}
function downloadCsv(filename, rows) {
  if (!rows?.length) return toast('There are no rows to export yet.');
  const blob = new Blob([buildCsv(rows)], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a'); link.href = url; link.download = filename; link.click();
  URL.revokeObjectURL(url);
}
function appendChat(role, text, meta = null) {
  const box = $('#chatMessages');
  const message = document.createElement('div');
  message.className = `chat-message ${role}`;
  message.innerHTML = markdownSafe(text);
  if (meta && role === 'assistant') {
    const trace = document.createElement('span');
    trace.className = 'trace-line';
    trace.textContent = `${meta.mode || 'agent'} · ${Number(meta.latency_ms || 0).toFixed(0)} ms${meta.trace_id ? ` · ${meta.trace_id}` : ''}`;
    message.appendChild(trace);
  }
  box.appendChild(message);
  box.scrollTop = box.scrollHeight;
}
function openChat() {
  $('#chatPanel').classList.add('open');
  $('#chatPanel').setAttribute('aria-hidden', 'false');
  if (!state.user) openLogin();
  else if (state.user.role === 'student') setTimeout(() => $('#chatInput')?.focus(), 180);
}
function closeChat() {
  // In the chatbot-first layout, the assistant is embedded in the page and stays visible.
  if (document.body.classList.contains('chat-first-layout')) {
    $('#chatPanel').classList.add('open');
    $('#chatPanel').setAttribute('aria-hidden', 'false');
    return;
  }
  $('#chatPanel').classList.remove('open');
  $('#chatPanel').setAttribute('aria-hidden', 'true');
}
function openLogin() {
  $('#loginError').classList.add('hidden');
  $('#loginModal').classList.remove('hidden');
  setTimeout(() => $('#username').focus(), 40);
}
function closeLogin() { $('#loginModal').classList.add('hidden'); }
async function sendChat(question = null) {
  if (!state.user) return openLogin();
  if (state.user.role !== 'student') return toast('Student chat is available to student accounts only.');
  const input = $('#chatInput');
  const raw = (question ?? input.value).trim();
  if (!raw || state.loading) return;
  if (raw.length > 4000) return toast('Please keep the message under 4,000 characters.');
  const visible = cleanCredentialText(raw);
  appendChat('user', visible);
  const history = [...state.chatHistory];
  state.chatHistory.push({ role: 'user', content: visible });
  if (state.chatHistory.length > 8) state.chatHistory = state.chatHistory.slice(-8);
  input.value = '';
  state.loading = true; $('#sendChat').disabled = true;
  const typing = document.createElement('div'); typing.className = 'typing-indicator'; typing.textContent = 'Selecting tools and relevant context…'; $('#chatMessages').appendChild(typing); $('#chatMessages').scrollTop = $('#chatMessages').scrollHeight;
  try {
    const payload = await api('/api/chat', { method: 'POST', body: JSON.stringify({ question: raw, consent: $('#memoryConsent').checked, history }) });
    typing.remove();
    appendChat('assistant', payload.result.answer || 'I could not formulate an answer.', payload.result);
    state.chatHistory.push({ role: 'assistant', content: cleanCredentialText(payload.result.answer || '') });
    if (state.chatHistory.length > 8) state.chatHistory = state.chatHistory.slice(-8);
  } catch (err) {
    typing.remove();
    appendChat('assistant', `I could not complete that request. ${err.message}`);
  } finally {
    state.loading = false; $('#sendChat').disabled = false; input.focus();
  }
}
async function performLogin(event) {
  event.preventDefault();
  const button = $('#loginSubmit');
  const error = $('#loginError');
  error.classList.add('hidden'); button.disabled = true; button.textContent = 'Signing in…';
  try {
    const result = await api('/api/login', { method: 'POST', body: JSON.stringify({ username: $('#username').value.trim(), password: $('#password').value }) });
    if (result.user?.role !== 'student') {
      await api('/api/logout', { method: 'POST', body: '{}' });
      throw new Error('Use a student demo account created with scripts/setup_demo_accounts.py for the Assignment 2 walkthrough.');
    }
    closeLogin();
    $('#password').value = '';
    setUser(result.user);
    toast(`Signed in as ${result.user.display_name || result.user.username}`);
    if (state.pendingOpenChat && result.user.role === 'student') { state.pendingOpenChat = false; openChat(); }
    if (state.user?.role === 'approver') $('#workspace').scrollIntoView({ behavior: 'smooth', block: 'start' });
    else if (state.user?.role === 'student') setTimeout(() => $('#chatInput')?.focus(), 80);
  } catch (err) {
    error.textContent = err.message; error.classList.remove('hidden');
  } finally {
    button.disabled = false; button.innerHTML = 'Sign in securely <span>→</span>';
  }
}
async function signOut() {
  try { await api('/api/logout', { method: 'POST', body: '{}' }); } catch { /* Local session still cleared client-side. */ }
  closeChat(); setUser(null); state.evaluation = null; state.panel = 'chat'; toast('You have signed out.'); window.scrollTo({ top: 0, behavior: 'smooth' });
}
async function runEvaluation() {
  const root = $('#workspaceContent');
  root.innerHTML = '<div class="content-card"><div class="loading-state"><span class="spinner"></span> Running the isolated evaluation suite. This can take a little while…</div></div>';
  try {
    const response = await api('/api/evaluation', { method: 'POST', body: '{}' });
    state.evaluation = response.report;
    root.innerHTML = renderEvaluationIntro(state.evaluation);
    toast(`Evaluation complete: ${state.evaluation.summary.passed}/${state.evaluation.summary.total} checks passed.`);
  } catch (err) {
    root.innerHTML = `<div class="content-card"><div class="result-banner error">${esc(err.message)}</div><button class="btn btn-primary" id="runEvaluation">Try again</button></div>`;
  }
}

// Main interactions are delegated so controls from dynamically rendered panels work too.
document.addEventListener('click', async event => {
  const target = event.target.closest('button,a');
  if (!target) return;
  if (target.matches('#loginOpen,[data-open-login]')) { event.preventDefault(); if (state.user) showWorkspace('chat'); else openLogin(); return; }
  if (target.matches('#heroChatButton,[data-open-chat]')) { event.preventDefault(); if (!state.user) state.pendingOpenChat = true; openChat(); return; }
  if (target.matches('#chatLauncher')) { openChat(); return; }
  if (target.matches('#closeChat')) { closeChat(); return; }
  if (target.matches('#closeLogin')) { closeLogin(); return; }
  if (target.matches('#logoutButton')) { await signOut(); return; }
  if (target.matches('#mobileNavToggle')) { const nav = $('#mainNav'); nav.classList.toggle('open'); target.setAttribute('aria-expanded', nav.classList.contains('open') ? 'true' : 'false'); return; }
  if (target.matches('[data-panel]')) { event.preventDefault(); showWorkspace(target.dataset.panel); return; }
  if (target.matches('#openChatFromPanel')) { openChat(); return; }
  if (target.matches('[data-prompt]')) { $('#chatInput').value = target.dataset.prompt; sendChat(); return; }
  if (target.matches('#runEvaluation')) { await runEvaluation(); return; }
  if (target.matches('#downloadEvaluation')) { if (state.evaluation) downloadCsv('aidtm_assignment1_evaluation.csv', state.evaluation.rows); return; }
  if (target.matches('#downloadTraces')) {
    try { const data = await api('/api/traces'); downloadCsv('aidtm_assignment1_trace_log.csv', data.traces || []); } catch (err) { toast(err.message); }
    return;
  }
  if (target.matches('[data-delete-memory]')) {
    if (!window.confirm('Delete this saved preference?')) return;
    try { await api(`/api/memory/${target.dataset.deleteMemory}`, { method: 'DELETE' }); toast('Preference deleted.'); renderPanel('records').catch(err => toast(err.message)); }
    catch (err) { toast(err.message); }
    return;
  }
});

document.addEventListener('submit', async event => {
  if (event.target.matches('#loginForm')) { await performLogin(event); return; }
  if (event.target.matches('#chatForm')) { event.preventDefault(); await sendChat(); return; }
  if (event.target.matches('#memoryForm')) {
    event.preventDefault(); const form = event.target; const values = Object.fromEntries(new FormData(form).entries());
    const consent = form.elements.consent.checked;
    try {
      const result = await api('/api/memory', { method: 'POST', body: JSON.stringify({ key: values.key, value: values.value, consent }) });
      toast(result.result?.message || 'Preference saved.'); await renderPanel('records');
    } catch (err) { toast(err.message); }
    return;
  }
  if (event.target.matches('#policySearch')) {
    event.preventDefault(); state.policyQuery = new FormData(event.target).get('query')?.toString() || '';
    const root = $('#workspaceContent'); root.innerHTML = '<div class="loading-state"><span class="spinner"></span> Retrieving relevant policy chunks…</div>';
    try { const data = await api(`/api/policy?q=${encodeURIComponent(state.policyQuery)}`); root.innerHTML = renderPolicy(data.chunks || [], data.result || null); }
    catch (err) { root.innerHTML = `<div class="result-banner error">${esc(err.message)}</div>`; }
    return;
  }
});

$('#loginModal').addEventListener('click', event => { if (event.target === $('#loginModal')) closeLogin(); });
document.addEventListener('keydown', event => { if (event.key === 'Escape') { closeLogin(); closeChat(); } });

async function bootstrap() {
  try { const response = await api('/api/me'); if (response.user?.role !== 'student') { await api('/api/logout', { method: 'POST', body: '{}' }); setUser(null); } else { setUser(response.user); } }
  catch { setUser(null); }
}
bootstrap();
