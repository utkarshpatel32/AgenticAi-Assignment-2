'use strict';

const http = require('node:http');
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const { spawn } = require('node:child_process');

const ROOT = __dirname;
const PUBLIC_DIR = path.join(ROOT, 'public');
const PORT = Number(process.env.PORT || 3000);
const HOST = process.env.HOST || '127.0.0.1';
const PYTHON = process.env.PYTHON || (process.platform === 'win32' ? 'python' : 'python3');
const SESSION_TTL_MS = 8 * 60 * 60 * 1000;
const sessions = new Map();

function sendJson(res, status, payload, extraHeaders = {}) {
  const body = JSON.stringify(payload);
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store',
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Content-Length': Buffer.byteLength(body),
    ...extraHeaders,
  });
  res.end(body);
}

function readBody(req, limit = 100_000) {
  return new Promise((resolve, reject) => {
    let data = '';
    req.on('data', chunk => {
      data += chunk;
      if (Buffer.byteLength(data) > limit) {
        reject(new Error('Request body is too large.'));
        req.destroy();
      }
    });
    req.on('end', () => {
      if (!data) return resolve({});
      try { resolve(JSON.parse(data)); }
      catch { reject(new Error('Request body must be valid JSON.')); }
    });
    req.on('error', reject);
  });
}

function runBridge(input) {
  return new Promise((resolve, reject) => {
    const child = spawn(PYTHON, ['-X', 'utf8', path.join(ROOT, 'bridge.py')], {
      cwd: ROOT,
      env: { ...process.env, PYTHONIOENCODING: 'utf-8:backslashreplace', PYTHONUTF8: '1' },
      stdio: ['pipe', 'pipe', 'pipe'],
      windowsHide: true,
    });
    let stdout = '';
    let stderr = '';
    child.stdout.setEncoding('utf8');
    child.stderr.setEncoding('utf8');
    child.stdout.on('data', chunk => { stdout += chunk; if (stdout.length > 2_000_000) child.kill(); });
    child.stderr.on('data', chunk => { stderr += chunk; if (stderr.length > 40_000) stderr = stderr.slice(-40_000); });
    child.on('error', err => reject(new Error(`Could not start Python backend (${PYTHON}): ${err.message}`)));
    child.on('close', code => {
      if (code !== 0 && !stdout.trim()) return reject(new Error(stderr.trim() || `Python backend exited with code ${code}`));
      try {
        const output = JSON.parse(stdout.trim());
        if (code !== 0 && output.ok !== false) return reject(new Error(stderr.trim() || 'Python backend failed.'));
        resolve(output);
      } catch (err) {
        reject(new Error(`Invalid response from Python backend. ${stderr.trim()}`));
      }
    });
    child.stdin.end(JSON.stringify(input));
  });
}

function parseCookies(header = '') {
  const result = {};
  for (const pair of header.split(';')) {
    const index = pair.indexOf('=');
    if (index < 0) continue;
    result[pair.slice(0, index).trim()] = decodeURIComponent(pair.slice(index + 1).trim());
  }
  return result;
}

function cookieHeader(value, maxAge = 28800) {
  const secure = process.env.NODE_ENV === 'production' ? '; Secure' : '';
  return `aidtm_session=${encodeURIComponent(value)}; HttpOnly; Path=/; SameSite=Lax; Max-Age=${maxAge}${secure}`;
}

async function getCurrentUser(req, res) {
  const sid = parseCookies(req.headers.cookie || '').aidtm_session;
  const session = sid && sessions.get(sid);
  if (!session || session.expiresAt < Date.now()) {
    if (sid) sessions.delete(sid);
    return null;
  }
  const check = await runBridge({ op: 'me', username: session.username });
  if (!check.ok || !check.user) {
    sessions.delete(sid);
    res.setHeader('Set-Cookie', cookieHeader('', 0));
    return null;
  }
  session.expiresAt = Date.now() + SESSION_TTL_MS;
  session.user = check.user;
  return { sid, user: check.user };
}

async function requireUser(req, res, roles = null) {
  const active = await getCurrentUser(req, res);
  if (!active) {
    sendJson(res, 401, { ok: false, error: 'Please sign in to continue.' });
    return null;
  }
  if (roles && !roles.includes(active.user.role)) {
    sendJson(res, 403, { ok: false, error: 'Your account does not have permission for this action.' });
    return null;
  }
  return active;
}

function safeStaticPath(urlPath) {
  let requested;
  try { requested = decodeURIComponent(urlPath.split('?')[0]); } catch { return null; }
  if (requested === '/') requested = '/index.html';
  const resolved = path.resolve(PUBLIC_DIR, '.' + requested);
  if (!resolved.startsWith(PUBLIC_DIR + path.sep) && resolved !== path.join(PUBLIC_DIR, 'index.html')) return null;
  return resolved;
}

function serveStatic(req, res, urlPath) {
  const filePath = safeStaticPath(urlPath);
  if (!filePath || !fs.existsSync(filePath) || !fs.statSync(filePath).isFile()) {
    res.writeHead(404, { 'Content-Type': 'text/plain; charset=utf-8', 'X-Content-Type-Options': 'nosniff' });
    res.end('Not found');
    return;
  }
  const ext = path.extname(filePath).toLowerCase();
  const types = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.svg': 'image/svg+xml', '.ico': 'image/x-icon' };
  res.writeHead(200, {
    'Content-Type': types[ext] || 'application/octet-stream',
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'strict-origin-when-cross-origin',
    'Cache-Control': ext === '.html' ? 'no-cache' : 'public, max-age=86400',
  });
  fs.createReadStream(filePath).pipe(res);
}

function apiPath(urlPath) { return urlPath.split('?')[0]; }

async function handleApi(req, res, urlObj) {
  const route = apiPath(urlObj.pathname);
  if (req.method === 'POST' && route === '/api/login') {
    const body = await readBody(req);
    const username = String(body.username || '').trim().slice(0, 80);
    const password = String(body.password || '').slice(0, 500);
    if (!username || !password) return sendJson(res, 400, { ok: false, error: 'Enter both username and password.' });
    const result = await runBridge({ op: 'login', username, password });
    if (!result.ok) return sendJson(res, 401, result);
    const sid = crypto.randomBytes(32).toString('base64url');
    sessions.set(sid, { username: result.user.username, user: result.user, expiresAt: Date.now() + SESSION_TTL_MS });
    return sendJson(res, 200, { ok: true, user: result.user }, { 'Set-Cookie': cookieHeader(sid) });
  }

  if (req.method === 'POST' && route === '/api/logout') {
    const sid = parseCookies(req.headers.cookie || '').aidtm_session;
    if (sid) sessions.delete(sid);
    return sendJson(res, 200, { ok: true }, { 'Set-Cookie': cookieHeader('', 0) });
  }

  if (req.method === 'GET' && route === '/api/me') {
    const active = await getCurrentUser(req, res);
    return active ? sendJson(res, 200, { ok: true, user: active.user }) : sendJson(res, 401, { ok: false });
  }

  if (req.method === 'POST' && route === '/api/chat') {
    const active = await requireUser(req, res, ['student']); if (!active) return;
    const body = await readBody(req);
    const result = await runBridge({ op: 'chat', username: active.user.username, question: body.question,
      consent: body.consent === true, history: Array.isArray(body.history) ? body.history.slice(-8) : [] });
    return sendJson(res, result.ok ? 200 : 400, result);
  }

  if (req.method === 'GET' && route === '/api/dashboard') {
    const active = await requireUser(req, res, ['student']); if (!active) return;
    return sendJson(res, 200, await runBridge({ op: 'dashboard', username: active.user.username }));
  }

  if (req.method === 'GET' && route === '/api/approvals') {
    const active = await requireUser(req, res, ['student', 'approver']); if (!active) return;
    return sendJson(res, 200, await runBridge({ op: 'approvals', username: active.user.username }));
  }

  const decisionMatch = route.match(/^\/api\/approvals\/([A-Za-z0-9-]+)\/decision$/);
  if (req.method === 'POST' && decisionMatch) {
    const active = await requireUser(req, res, ['approver']); if (!active) return;
    const body = await readBody(req);
    const result = await runBridge({ op: 'decide_approval', username: active.user.username, request_id: decisionMatch[1], approve: body.approve === true, note: body.note || '' });
    return sendJson(res, result.ok ? 200 : 400, result);
  }

  if (req.method === 'GET' && route === '/api/audit') {
    const active = await requireUser(req, res, ['student', 'approver']); if (!active) return;
    return sendJson(res, 200, await runBridge({ op: 'audit', username: active.user.username }));
  }

  if (req.method === 'GET' && route === '/api/traces') {
    const active = await requireUser(req, res, ['student', 'approver']); if (!active) return;
    return sendJson(res, 200, await runBridge({ op: 'traces', username: active.user.username }));
  }

  if (req.method === 'GET' && route === '/api/knowledge') {
    const active = await requireUser(req, res, ['student', 'approver']); if (!active) return;
    const query = urlObj.searchParams.get('q') || '';
    return sendJson(res, 200, await runBridge({ op: 'knowledge_search', username: active.user.username, query }));
  }

  if (req.method === 'GET' && route === '/api/policy') {
    const active = await requireUser(req, res, ['student']); if (!active) return;
    const query = urlObj.searchParams.get('q') || '';
    return sendJson(res, 200, await runBridge({ op: 'policy_search', username: active.user.username, query }));
  }

  if (req.method === 'POST' && route === '/api/evaluation') {
    const active = await requireUser(req, res, ['student', 'approver']); if (!active) return;
    return sendJson(res, 200, await runBridge({ op: 'evaluation', username: active.user.username }));
  }

  if (req.method === 'POST' && route === '/api/memory') {
    const active = await requireUser(req, res, ['student']); if (!active) return;
    const body = await readBody(req);
    const result = await runBridge({ op: 'save_memory', username: active.user.username, key: body.key, value: body.value, consent: body.consent === true });
    return sendJson(res, result.ok ? 200 : 400, result);
  }

  const deleteMemoryMatch = route.match(/^\/api\/memory\/([0-9]+)$/);
  if (req.method === 'DELETE' && deleteMemoryMatch) {
    const active = await requireUser(req, res, ['student']); if (!active) return;
    const result = await runBridge({ op: 'delete_memory', username: active.user.username, memory_id: deleteMemoryMatch[1] });
    return sendJson(res, result.ok ? 200 : 400, result);
  }

  return sendJson(res, 404, { ok: false, error: 'API route not found.' });
}

const server = http.createServer(async (req, res) => {
  try {
    const urlObj = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
    if (urlObj.pathname.startsWith('/api/')) {
      if (!['GET', 'POST', 'DELETE'].includes(req.method)) return sendJson(res, 405, { ok: false, error: 'Method not allowed.' }, { Allow: 'GET, POST, DELETE' });
      await handleApi(req, res, urlObj);
      return;
    }
    if (req.method !== 'GET' && req.method !== 'HEAD') {
      res.writeHead(405, { 'Content-Type': 'text/plain; charset=utf-8', Allow: 'GET, HEAD' });
      res.end('Method not allowed');
      return;
    }
    serveStatic(req, res, req.url);
  } catch (err) {
    console.error(`[${new Date().toISOString()}] request failed: ${err.message}`);
    if (!res.headersSent) sendJson(res, 500, { ok: false, error: err.message || 'Unexpected server error.' });
    else res.end();
  }
});

server.listen(PORT, HOST, () => {
  console.log(`AIDTM Smart Campus AI is running at http://${HOST}:${PORT}`);
  console.log('Node.js serves the UI; Python bridge provides the existing safety-aware agent.');
  console.log('Create local student/approver logins with: python scripts/setup_demo_accounts.py');
});

function sweepExpiredSessions() {
  const now = Date.now();
  for (const [sid, session] of sessions.entries()) if (session.expiresAt < now) sessions.delete(sid);
}
setInterval(sweepExpiredSessions, 10 * 60 * 1000).unref();

process.on('SIGINT', () => { server.close(() => process.exit(0)); });
process.on('SIGTERM', () => { server.close(() => process.exit(0)); });
