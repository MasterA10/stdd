#!/usr/bin/env node

const http = require('http');
const fs = require('fs');
const path = require('path');
const { exec } = require('child_process');

const PORT = 8765;
const CWD = process.cwd();
const DIST_DIR = path.join(__dirname, '..', 'dist');
const DRAWS_DIR = path.join(CWD, '.stdd', 'draws');

// Ensure the local draws directory exists in the target project workspace
if (!fs.existsSync(DRAWS_DIR)) {
  fs.mkdirSync(DRAWS_DIR, { recursive: true });
}

// Ensure local index.json exists, if not initialize it as empty array
const indexFile = path.join(DRAWS_DIR, 'index.json');
if (!fs.existsSync(indexFile)) {
  fs.writeFileSync(indexFile, JSON.stringify([], null, 2));
}

const MIME_TYPES = {
  '.html': 'text/html',
  '.css': 'text/css',
  '.js': 'application/javascript',
  '.json': 'application/json',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.svg': 'image/svg+xml',
  '.ico': 'image/x-icon'
};

const server = http.createServer((req, res) => {
  // CORS Headers
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  const url = new URL(req.url, `http://${req.headers.host}`);
  const pathname = url.pathname;

  // --- API Endpoint: Get Draws Index ---
  if (req.method === 'GET' && pathname === '/.stdd/draws/index.json') {
    fs.readFile(indexFile, 'utf8', (err, data) => {
      if (err) {
        res.writeHead(500, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Failed to read drawings index' }));
        return;
      }
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(data);
    });
    return;
  }

  // --- API Endpoint: Get Single Draw ---
  if (req.method === 'GET' && pathname.startsWith('/.stdd/draws/') && pathname.endsWith('.json')) {
    const filename = path.basename(pathname);
    const filePath = path.join(DRAWS_DIR, filename);

    fs.readFile(filePath, 'utf8', (err, data) => {
      if (err) {
        res.writeHead(404, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Drawing file not found' }));
        return;
      }
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(data);
    });
    return;
  }

  // --- API Endpoint: Save Single Draw ---
  if (req.method === 'POST' && (pathname.startsWith('/.stdd/draws/') || pathname.startsWith('/__stdd/api/draws/')) && pathname.endsWith('.json')) {
    const filename = path.basename(pathname);
    const filePath = path.join(DRAWS_DIR, filename);
    const drawId = filename.replace('.json', '');

    let body = '';
    req.on('data', chunk => { body += chunk; });
    req.on('end', () => {
      try {
        const payload = JSON.parse(body);

        // Save drawing file
        fs.writeFileSync(filePath, JSON.stringify(payload, null, 2));

        // Update index.json automatically to register this drawing
        let indexData = [];
        try {
          indexData = JSON.parse(fs.readFileSync(indexFile, 'utf8'));
        } catch (_) {}

        const existingIdx = indexData.findIndex(item => item.id === drawId);
        const drawMeta = {
          id: drawId,
          title: payload.title || drawId,
          subtitle: payload.subtitle || '',
          kind: payload.kind || 'flow'
        };

        if (existingIdx >= 0) {
          indexData[existingIdx] = drawMeta;
        } else {
          indexData.push(drawMeta);
        }

        fs.writeFileSync(indexFile, JSON.stringify(indexData, null, 2));

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: true, message: 'Drawing saved successfully' }));
      } catch (err) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ error: 'Invalid JSON payload' }));
      }
    });
    return;
  }

  // --- Static Asset Server (dist folder) ---
  let filePath = path.join(DIST_DIR, pathname === '/' ? 'index.html' : pathname);

  // Fallback to index.html for client-side routing
  if (!fs.existsSync(filePath)) {
    filePath = path.join(DIST_DIR, 'index.html');
  }

  const ext = path.extname(filePath).toLowerCase();
  const contentType = MIME_TYPES[ext] || 'application/octet-stream';

  fs.readFile(filePath, (err, content) => {
    if (err) {
      res.writeHead(404, { 'Content-Type': 'text/plain' });
      res.end('File not found');
      return;
    }
    res.writeHead(200, { 'Content-Type': contentType });
    res.end(content);
  });
});

server.listen(PORT, () => {
  const url = `http://localhost:${PORT}`;
  console.log(`\x1b[32m✔ STDD Flow Editor running globally!\x1b[0m`);
  console.log(`\x1b[36m📂 Workspace directory:\x1b[0m ${CWD}`);
  console.log(`\x1b[36m📝 Drawings directory:\x1b[0m ${DRAWS_DIR}`);
  console.log(`\x1b[35m🔌 Server URL:\x1b[0m ${url}\n`);

  // Auto-open browser based on platform
  const startCmd = process.platform === 'darwin' ? 'open' : process.platform === 'win32' ? 'start' : 'xdg-open';
  exec(`${startCmd} ${url}`);
});
