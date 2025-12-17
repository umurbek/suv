// Simple helper for API calls from Cordova app
// Uses API_BASE from config.js and sends credentials when needed.

import { API_BASE } from './config.js';

async function apiFetch(path, options = {}){
    const url = (API_BASE || '') + path.replace(/^\//, '');
    const opts = Object.assign({
        method: 'GET',
        credentials: 'include', // send cookies for session-based auth
        headers: { 'X-Requested-With': 'XMLHttpRequest' }
    }, options);

    // If body is a JS object, convert to JSON
    if (opts.body && typeof opts.body === 'object' && !(opts.body instanceof FormData)){
        opts.headers['Content-Type'] = 'application/json';
        opts.body = JSON.stringify(opts.body);
    }

    const resp = await fetch(url, opts);
    // try parse JSON safely
    let data = null;
    try{ data = await resp.json(); } catch(e) { data = null; }
    return { status: resp.status, ok: resp.ok, data };
}

export { apiFetch, API_BASE };
