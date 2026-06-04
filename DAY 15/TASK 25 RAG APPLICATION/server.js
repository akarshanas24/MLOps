const http = require('http');
const https = require('https');
const fs = require('fs').promises;
const path = require('path');

const basePort = Number(process.env.PORT) || 3010;
const fastAPIBaseURL = process.env.FASTAPI_URL || 'http://127.0.0.1:8000';
const publicDir = __dirname;

const backendData = {
  metrics: {
    farmersSupported: 3520,
    marketReports: 18740,
    governmentSchemes: 620,
    cropCategories: 48,
    schemeCount: 14,
  },
  schemes: [
    { id: 1, name: 'Soil Health Grant', status: 'Active', description: 'Funding support for soil quality improvements.' },
    { id: 2, name: 'Crop Insurance Relief', status: 'Recommended', description: 'Subsidized coverage for weather and crop losses.' },
    { id: 3, name: 'Irrigation Upgrade', status: 'New', description: 'Low-cost financing for efficient irrigation systems.' },
    { id: 4, name: 'Organic Farming Incentive', status: 'Active', description: 'Support for transitioning to organic practices.' },
  ],
  assistant: {
    greeting: 'Welcome to AgriIntel backend. Ask for market signals, scheme help, or crop planning advice.',
  },
};

const sendJson = (res, code, payload) => {
  res.writeHead(code, {
    'Content-Type': 'application/json; charset=utf-8',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  });
  res.end(JSON.stringify(payload));
};

const proxyRequest = (method, path, body) => {
  return new Promise((resolve, reject) => {
    const url = new URL(fastAPIBaseURL);
    const options = {
      hostname: url.hostname,
      port: url.port || (url.protocol === 'https:' ? 443 : 80),
      path: path,
      method: method,
      headers: {
        'Content-Type': 'application/json',
        'Content-Length': body ? Buffer.byteLength(body) : 0,
      },
    };

    const protocol = url.protocol === 'https:' ? https : http;
    const req = protocol.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => { data += chunk; });
      res.on('end', () => {
        try {
          resolve({ status: res.statusCode, body: JSON.parse(data) });
        } catch (e) {
          resolve({ status: res.statusCode, body: { error: data } });
        }
      });
    });

    req.on('error', (error) => {
      console.error(`Proxy error for ${method} ${path}:`, error.message);
      reject({ error: `FastAPI unavailable: ${error.message}` });
    });

    if (body) req.write(body);
    req.end();
  });
};

const serveStatic = async (filePath, contentType, res) => {
  try {
    const file = await fs.readFile(filePath);
    res.writeHead(200, { 'Content-Type': contentType });
    res.end(file);
  } catch (error) {
    res.writeHead(404, { 'Content-Type': 'text/plain' });
    res.end('Not found');
  }
};

const requestListener = async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);

  if (req.method === 'OPTIONS') {
    sendJson(res, 204, {});
    return;
  }

  if (url.pathname === '/api/insights' && req.method === 'GET') {
    sendJson(res, 200, { metrics: backendData.metrics });
    return;
  }

  if (url.pathname === '/api/schemes' && req.method === 'GET') {
    sendJson(res, 200, { schemes: backendData.schemes });
    return;
  }

  if (url.pathname === '/api/query' && req.method === 'POST') {
    let body = '';
    req.on('data', (chunk) => { body += chunk; });
    req.on('end', async () => {
      try {
        const payload = JSON.parse(body || '{}');
        const query = String(payload.query || '').trim();
        if (!query) {
          sendJson(res, 400, { error: 'Query field required' });
          return;
        }
        try {
          const result = await proxyRequest('POST', '/query', body);
          sendJson(res, result.status || 200, result.body);
        } catch (proxyError) {
          sendJson(res, 503, { error: proxyError.error || 'Backend unavailable' });
        }
      } catch (error) {
        sendJson(res, 400, { error: 'Invalid JSON body' });
      }
    });
    return;
  }

  if (url.pathname === '/api/ingest' && req.method === 'POST') {
    let body = '';
    req.on('data', (chunk) => { body += chunk; });
    req.on('end', async () => {
      try {
        const payload = JSON.parse(body || '{}');
        if (!payload.paths || !Array.isArray(payload.paths)) {
          sendJson(res, 400, { error: 'paths array required' });
          return;
        }
        try {
          const result = await proxyRequest('POST', '/ingest', body);
          sendJson(res, result.status || 200, result.body);
        } catch (proxyError) {
          sendJson(res, 503, { error: proxyError.error || 'Backend unavailable' });
        }
      } catch (error) {
        sendJson(res, 400, { error: 'Invalid JSON body' });
      }
    });
    return;
  }

  if (url.pathname === '/api/chat' && req.method === 'POST') {
    let body = '';
    req.on('data', (chunk) => { body += chunk; });
    req.on('end', async () => {
      try {
        const payload = JSON.parse(body || '{}');
        const question = String(payload.message || '').trim();
        if (!question) {
          sendJson(res, 200, { reply: 'Please ask a specific question about agricultural topics, schemes, or crop advice.' });
          return;
        }
        try {
          const ragResult = await proxyRequest('POST', '/query', JSON.stringify({ query: question, top_k: 5, model: 'llama3' }));
          const reply = ragResult.body.answer || ragResult.body.error || 'Unable to process query';
          sendJson(res, 200, { reply: reply, sources: ragResult.body.sources });
        } catch (proxyError) {
          sendJson(res, 200, { reply: 'Backend service is currently offline. Please ensure Ollama is running and FastAPI server is started.' });
        }
      } catch (error) {
        sendJson(res, 400, { error: 'Invalid JSON body' });
      }
    });
    return;
  }

  const pathname = url.pathname === '/' ? '/index.html' : url.pathname;
  const filePath = path.join(publicDir, pathname);
  const ext = path.extname(filePath).toLowerCase();
  const contentTypes = {
    '.html': 'text/html; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.js': 'application/javascript; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
  };

  if (Object.prototype.hasOwnProperty.call(contentTypes, ext)) {
    await serveStatic(filePath, contentTypes[ext], res);
    return;
  }

  res.writeHead(404, { 'Content-Type': 'text/plain' });
  res.end('Not found');
};

const createServer = () => http.createServer(requestListener);
const MAX_PORT_ATTEMPTS = 5;

const listenOnPort = (listenPort, attempts = 0) => {
  if (attempts >= MAX_PORT_ATTEMPTS) {
    console.error(`Could not start server after ${attempts} attempts. Please free a port and try again.`);
    process.exit(1);
  }

  const server = createServer();
  server.on('error', (error) => {
    if (error.code === 'EADDRINUSE') {
      const nextPort = listenPort + 1;
      console.warn(`Port ${listenPort} is in use. Trying ${nextPort}...`);
      listenOnPort(nextPort, attempts + 1);
    } else {
      console.error('Server error:', error);
      process.exit(1);
    }
  });

  server.listen(listenPort, () => {
    console.log(`AgriIntel backend running at http://localhost:${listenPort}`);
  });
};

listenOnPort(basePort);
