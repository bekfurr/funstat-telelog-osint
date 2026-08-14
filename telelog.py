#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FUNSTAT OSINT WEB INTERFACE
BEKFURR // BEKFURR
Flask proxy + vanilla JS frontend. All Funstat API v1 endpoints exposed.
Generic GET forwarding preserves every query parameter, including arrays.
"""

import os
import requests
from flask import Flask, request, jsonify, render_template_string

# ----------------------------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------------------------
FUNSTAT_BASE_URL = os.environ.get("FUNSTAT_BASE_URL", "https://funstat.info")
DEFAULT_TOKEN = os.environ.get("FUNSTAT_TOKEN", "")  # optional default token

# ----------------------------------------------------------------------
# FUNSTAT CLIENT (funstat-api equivalent)
# ----------------------------------------------------------------------
class FunstatClient:
    """Minimal Python client for Funstat API v1.

    All endpoints are GET. The client forwards any query parameters as-is,
    including repeated keys for arrays (e.g. id=1&id=2&id=3).
    """

    def __init__(self, base_url: str = FUNSTAT_BASE_URL, token: str = DEFAULT_TOKEN):
        self.base_url = base_url.rstrip("/")
        self.token = token

    def _headers(self, incoming_auth: str = None) -> dict:
        headers = {"Accept": "application/json"}
        # Use incoming Authorization header if present, else stored token
        if incoming_auth:
            headers["Authorization"] = incoming_auth
        elif self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def get(self, path: str, params: dict = None, auth_header: str = None):
        """Perform a GET request to the Funstat API.

        Args:
            path: API path, e.g. '/api/v1/users/123/stats'
            params: dictionary of query parameters. Values can be lists for arrays.
            auth_header: raw Authorization header value to forward.
        Returns:
            dict with keys: status_code, json (or None), error (or None)
        """
        url = self.base_url + path
        # Ensure params is dict; list values become repeated keys automatically
        query_params = []
        if params:
            for key, value in params.items():
                if isinstance(value, (list, tuple)):
                    for v in value:
                        query_params.append((key, str(v)))
                else:
                    query_params.append((key, str(value)))
        try:
            resp = requests.get(
                url,
                params=query_params,
                headers=self._headers(auth_header),
                timeout=30,
            )
            try:
                data = resp.json()
            except Exception:
                data = resp.text
            return {
                "status_code": resp.status_code,
                "json": data,
                "error": None,
            }
        except Exception as e:
            return {
                "status_code": 500,
                "json": None,
                "error": str(e),
            }

# ----------------------------------------------------------------------
# FLASK APP
# ----------------------------------------------------------------------
app = Flask(__name__)
client = FunstatClient()

# ----------------------------------------------------------------------
# PROXY ROUTE
# ----------------------------------------------------------------------
@app.route("/proxy")
def proxy():
    """
    Forward GET request to Funstat.
    Required query parameter: `path` (e.g. /api/v1/users/123/stats)
    All other query parameters are forwarded unchanged.
    The incoming Authorization header (Bearer token) is forwarded to Funstat.
    """
    path = request.args.get("path")
    if not path:
        return jsonify({"success": False, "error": "Missing 'path' query parameter"}), 400

    # Collect remaining query params (excluding 'path')
    params = {}
    for key, value in request.args.items():
        if key == "path":
            continue
        if key in params:
            # repeated key -> list
            if isinstance(params[key], list):
                params[key].append(value)
            else:
                params[key] = [params[key], value]
        else:
            params[key] = value

    auth_header = request.headers.get("Authorization")
    result = client.get(path, params=params, auth_header=auth_header)

    return jsonify(result), result["status_code"]

# ----------------------------------------------------------------------
# FRONTEND (embedded HTML/JS)
# ----------------------------------------------------------------------
INDEX_HTML = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>FUNSTAT OSINT CONSOLE // BEKFURR INC 2026</title>
<style>
  :root {
    --bg: #0a0e12; --panel: #11181f; --border: #1f2b36;
    --text: #c9d1d9; --dim: #6e7b87; --accent: #00b4d8;
    --ok: #2ecc71; --err: #e74c3c; --warn: #f39c12;
    --mono: 'Courier New', monospace;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font-family: var(--mono); padding: 1rem; line-height: 1.4; }
  header { border-bottom: 2px solid var(--accent); padding-bottom: 0.5rem; margin-bottom: 1rem; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 1rem; }
  h1 { color: var(--accent); font-size: 1.4rem; letter-spacing: 1px; }
  .config { display: flex; gap: 1rem; flex-wrap: wrap; align-items: center; }
  .config label { font-size: 0.8rem; color: var(--dim); display: flex; flex-direction: column; gap: 0.2rem; }
  .config input { background: #0d1419; border: 1px solid var(--border); color: var(--text); padding: 0.4rem 0.6rem; font-family: var(--mono); font-size: 0.9rem; min-width: 220px; }
  .config button { background: var(--accent); border: none; color: #000; padding: 0.5rem 1rem; font-weight: bold; cursor: pointer; font-family: var(--mono); letter-spacing: 1px; }
  .layout { display: grid; grid-template-columns: 260px 1fr; gap: 1rem; height: calc(100vh - 100px); }
  nav { background: var(--panel); border: 1px solid var(--border); overflow-y: auto; padding: 0.5rem; font-size: 0.85rem; }
  nav .group { color: var(--warn); margin: 0.8rem 0 0.3rem; font-weight: bold; letter-spacing: 1px; }
  nav button { display: block; width: 100%; text-align: left; background: none; border: none; color: var(--dim); padding: 0.35rem 0.5rem; cursor: pointer; font-family: var(--mono); font-size: 0.8rem; border-left: 2px solid transparent; }
  nav button:hover { background: #1a242e; color: var(--text); }
  nav button.active { border-left-color: var(--accent); color: var(--accent); background: #16212b; }
  main { background: var(--panel); border: 1px solid var(--border); overflow-y: auto; padding: 1rem; }
  .endpoint { display: none; }
  .endpoint.active { display: block; }
  .ep-header { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 0.5rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; margin-bottom: 1rem; }
  .ep-title { font-size: 1.1rem; color: var(--accent); }
  .ep-meta { font-size: 0.75rem; color: var(--dim); }
  .form-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 0.8rem; margin-bottom: 1rem; }
  .field { display: flex; flex-direction: column; gap: 0.2rem; }
  .field label { font-size: 0.75rem; color: var(--dim); text-transform: uppercase; letter-spacing: 0.5px; }
  .field input, .field select { background: #0d1419; border: 1px solid var(--border); color: var(--text); padding: 0.4rem 0.6rem; font-family: var(--mono); font-size: 0.9rem; }
  .field input[type="checkbox"] { width: auto; align-self: flex-start; }
  .field .hint { font-size: 0.7rem; color: var(--dim); }
  .actions { display: flex; gap: 0.5rem; align-items: center; flex-wrap: wrap; margin-bottom: 1rem; }
  .actions button { background: var(--accent); border: none; color: #000; padding: 0.5rem 1rem; font-weight: bold; cursor: pointer; font-family: var(--mono); }
  .status { margin: 0.8rem 0; padding: 0.5rem; border-left: 3px solid var(--warn); background: #1a1f24; font-size: 0.8rem; display: none; }
  .status.ok { border-color: var(--ok); color: var(--ok); display: block; }
  .status.err { border-color: var(--err); color: var(--err); display: block; }
  pre { background: #0d1419; border: 1px solid var(--border); padding: 1rem; overflow: auto; font-size: 0.8rem; max-height: 400px; white-space: pre-wrap; word-break: break-all; }
  .tech { display: flex; gap: 1rem; font-size: 0.8rem; color: var(--dim); margin-bottom: 0.5rem; flex-wrap: wrap; }
  .tech span { background: #1a242e; padding: 0.2rem 0.5rem; border-radius: 3px; }
</style>
</head>
<body>
<header>
  <h1>[ FUNSTAT OSINT // BEKFURR ]</h1>
  <div class="config">
    <label>BEARER TOKEN
      <input type="password" id="token" placeholder="Paste JWT token" autocomplete="off">
    </label>
    <button id="saveToken">SAVE</button>
  </div>
</header>
<div class="layout">
  <nav id="nav"></nav>
  <main id="main"></main>
</div>
<script>
(() => {
  // ---- endpoint definitions ----
  const endpoints = [
    { group:'GROUPS', key:'common_groups', title:'Common Groups', path:'/api/v1/groups/common_groups',
      params:[{name:'id', type:'array', hint:'Comma-separated user IDs. Cost 0.5'}], desc:'Return common groups of specified users.' },
    { group:'GROUPS', key:'group_info', title:'Group Info', path:'/api/v1/groups/{id}',
      pathParams:[{name:'id', type:'integer', required:true, hint:'Group ID'}], desc:'Group basic info, links and today stats. Cost 0.01' },
    { group:'GROUPS', key:'group_members', title:'Group Members', path:'/api/v1/groups/{id}/members',
      pathParams:[{name:'id', type:'integer', required:true, hint:'Group ID'}], desc:'Group members. Cost 15' },
    { group:'USERS', key:'gifts_relation', title:'Gifts Relation', path:'/api/v1/users/{id}/gifts_relation',
      pathParams:[{name:'id', type:'integer', required:true, hint:'User ID'}],
      params:[{name:'page', type:'integer', default:1}, {name:'pageSize', type:'integer', default:20}], desc:'Gifts FROM/TO. Cost 5 if >5 relations.' },
    { group:'USERS', key:'stickers', title:'Sticker Packs', path:'/api/v1/users/{id}/stickers',
      pathParams:[{name:'id', type:'integer', required:true, hint:'User ID'}], desc:'Sticker packs created by user. Cost 1 if found.' },
    { group:'USERS', key:'common_groups_stat', title:'Common Groups Stat', path:'/api/v1/users/{id}/common_groups_stat',
      pathParams:[{name:'id', type:'integer', required:true, hint:'User ID'}], desc:'Users with common groups. Cost 5.' },
    { group:'USERS', key:'reputation', title:'Reputation', path:'/api/v1/users/reputation',
      params:[{name:'id', type:'integer', hint:'User ID'}], desc:'User reputation info. FREE.' },
    { group:'USERS', key:'name_usage', title:'Name Usage', path:'/api/v1/users/name_usage',
      params:[{name:'name', type:'string', required:true, hint:'Search name'}, {name:'page', type:'integer', default:1}, {name:'pageSize', type:'integer', default:20}], desc:'Search by name.' },
    { group:'USERS', key:'username_usage', title:'Username Usage', path:'/api/v1/users/username_usage',
      params:[{name:'username', type:'string', required:true, hint:'@username'}], desc:'Username usage. Cost 0.1.' },
    { group:'USERS', key:'resolve_username', title:'Resolve Username', path:'/api/v1/users/resolve_username',
      params:[{name:'name', type:'array', required:true, hint:'Comma-separated @usernames'}], desc:'Resolve usernames. Cost 0.1 per success.' },
    { group:'USERS', key:'stats_min', title:'Stats Min', path:'/api/v1/users/{id}/stats_min',
      pathParams:[{name:'id', type:'integer', required:true, hint:'User ID'}], desc:'Basic stats. FREE.' },
    { group:'USERS', key:'stats', title:'Full Stats', path:'/api/v1/users/{id}/stats',
      pathParams:[{name:'id', type:'integer', required:true, hint:'User ID'}], desc:'Full stats. Cost 1.' },
    { group:'USERS', key:'basic_info_by_id', title:'Basic Info by ID', path:'/api/v1/users/basic_info_by_id',
      params:[{name:'id', type:'array', required:true, hint:'Comma-separated user IDs'}], desc:'Get user info by telegram ID. Cost 0.1 per success.' },
    { group:'USERS', key:'groups_count', title:'Groups Count', path:'/api/v1/users/{id}/groups_count',
      pathParams:[{name:'id', type:'integer', required:true, hint:'User ID'}],
      params:[{name:'onlyMsg', type:'boolean', default:true, hint:'Only groups with messages'}], desc:'Total group count. FREE.' },
    { group:'USERS', key:'messages', title:'Messages', path:'/api/v1/users/{id}/messages',
      pathParams:[{name:'id', type:'integer', required:true, hint:'User ID'}],
      params:[
        {name:'group_id', type:'integer', hint:'Filter by group ID'},
        {name:'text_contains', type:'string', hint:'Filter by text'},
        {name:'media_code', type:'integer', hint:'Filter by media code'},
        {name:'page', type:'integer', default:1},
        {name:'pageSize', type:'integer', default:20}
      ], desc:'User messages. Cost 10 if >100 msgs.' },
    { group:'USERS', key:'messages_count', title:'Messages Count', path:'/api/v1/users/{id}/messages_count',
      pathParams:[{name:'id', type:'integer', required:true, hint:'User ID'}], desc:'Total message count. FREE.' },
    { group:'USERS', key:'groups', title:'Known Groups', path:'/api/v1/users/{id}/groups',
      pathParams:[{name:'id', type:'integer', required:true, hint:'User ID'}], desc:'Known user groups. Cost 5.' },
    { group:'USERS', key:'names', title:'Names History', path:'/api/v1/users/{id}/names',
      pathParams:[{name:'id', type:'integer', required:true, hint:'User ID'}], desc:'First/last name history. Cost 3.' },
    { group:'USERS', key:'usernames', title:'Usernames History', path:'/api/v1/users/{id}/usernames',
      pathParams:[{name:'id', type:'integer', required:true, hint:'User ID'}], desc:'@username history. Cost 3.' },
    { group:'TEXT', key:'text_search', title:'Text Search', path:'/api/v1/text/search',
      params:[{name:'input', type:'string', required:true, hint:'Text to search'}, {name:'page', type:'integer', default:1}, {name:'pageSize', type:'integer', default:20}], desc:'Search who/when/where wrote text. Cost 0.1.' }
  ];

  // ---- state ----
  let activeKey = endpoints[0].key;
  const nav = document.getElementById('nav');
  const main = document.getElementById('main');
  const tokenInput = document.getElementById('token');

  // load token
  tokenInput.value = localStorage.getItem('funstat_token') || '';
  document.getElementById('saveToken').addEventListener('click', () => {
    localStorage.setItem('funstat_token', tokenInput.value.trim());
  });

  // render nav
  function renderNav() {
    nav.innerHTML = '';
    let lastGroup = '';
    endpoints.forEach(ep => {
      if (ep.group !== lastGroup) {
        const g = document.createElement('div');
        g.className = 'group';
        g.textContent = ep.group;
        nav.appendChild(g);
        lastGroup = ep.group;
      }
      const btn = document.createElement('button');
      btn.textContent = ep.title;
      btn.className = ep.key === activeKey ? 'active' : '';
      btn.addEventListener('click', () => setActive(ep.key));
      nav.appendChild(btn);
    });
  }

  function setActive(key) {
    activeKey = key;
    renderNav();
    renderEndpoint();
  }

  // render selected endpoint
  function renderEndpoint() {
    const ep = endpoints.find(e => e.key === activeKey);
    if (!ep) return;
    main.innerHTML = '';
    const div = document.createElement('div');
    div.className = 'endpoint active';
    div.id = 'ep-' + ep.key;

    const header = document.createElement('div');
    header.className = 'ep-header';
    header.innerHTML = `<span class="ep-title">${ep.title}</span><span class="ep-meta">${ep.path}</span>`;
    div.appendChild(header);

    const desc = document.createElement('div');
    desc.className = 'ep-meta';
    desc.textContent = ep.desc;
    div.appendChild(desc);

    // form grid
    const formGrid = document.createElement('div');
    formGrid.className = 'form-grid';

    // path params
    if (ep.pathParams) {
      ep.pathParams.forEach(p => {
        formGrid.appendChild(createField(p, 'path_'));
      });
    }
    // query params
    if (ep.params) {
      ep.params.forEach(p => {
        formGrid.appendChild(createField(p, 'q_'));
      });
    }
    div.appendChild(formGrid);

    // actions
    const actions = document.createElement('div');
    actions.className = 'actions';
    const runBtn = document.createElement('button');
    runBtn.textContent = 'EXECUTE';
    runBtn.addEventListener('click', () => execute(ep));
    actions.appendChild(runBtn);
    div.appendChild(actions);

    // status
    const status = document.createElement('div');
    status.className = 'status';
    status.id = 'status-' + ep.key;
    div.appendChild(status);

    // pre for JSON
    const pre = document.createElement('pre');
    pre.id = 'result-' + ep.key;
    div.appendChild(pre);

    main.appendChild(div);
  }

  function createField(param, prefix) {
    const field = document.createElement('div');
    field.className = 'field';
    const label = document.createElement('label');
    label.textContent = param.name + (param.required ? ' *' : '');
    field.appendChild(label);

    if (param.type === 'boolean') {
      const input = document.createElement('input');
      input.type = 'checkbox';
      input.id = prefix + param.name;
      input.checked = param.default !== undefined ? param.default : false;
      field.appendChild(input);
    } else {
      const input = document.createElement('input');
      input.type = 'text';
      input.id = prefix + param.name;
      if (param.default !== undefined) input.value = param.default;
      input.placeholder = param.hint || '';
      field.appendChild(input);
    }
    if (param.hint) {
      const hint = document.createElement('span');
      hint.className = 'hint';
      hint.textContent = param.hint;
      field.appendChild(hint);
    }
    return field;
  }

  function getValue(prefix, name) {
    const el = document.getElementById(prefix + name);
    if (!el) return undefined;
    if (el.type === 'checkbox') return el.checked;
    return el.value.trim();
  }

  function buildPath(ep) {
    let path = ep.path;
    if (ep.pathParams) {
      ep.pathParams.forEach(p => {
        const v = getValue('path_', p.name);
        if (!v && p.required) throw new Error(`Missing required path param: ${p.name}`);
        path = path.replace(`{${p.name}}`, encodeURIComponent(v || ''));
      });
    }
    return path;
  }

  function buildQueryString(ep) {
    const params = ep.params || [];
    const parts = [];
    params.forEach(p => {
      const v = getValue('q_', p.name);
      if (v === undefined || v === null || v === '') return;
      if (p.type === 'array') {
        // split comma-separated and append repeated keys
        const arr = String(v).split(',').map(x => x.trim()).filter(x => x);
        arr.forEach(item => parts.push(`${encodeURIComponent(p.name)}=${encodeURIComponent(item)}`));
      } else if (p.type === 'boolean') {
        parts.push(`${p.name}=${v}`);
      } else {
        parts.push(`${encodeURIComponent(p.name)}=${encodeURIComponent(v)}`);
      }
    });
    return parts.join('&');
  }

  async function execute(ep) {
    const statusEl = document.getElementById('status-' + ep.key);
    const preEl = document.getElementById('result-' + ep.key);
    statusEl.className = 'status';
    statusEl.style.display = 'none';
    preEl.textContent = '';

    let path, queryString;
    try {
      path = buildPath(ep);
      queryString = buildQueryString(ep);
    } catch (e) {
      statusEl.textContent = e.message;
      statusEl.className = 'status err';
      return;
    }

    const token = tokenInput.value.trim();
    if (!token) {
      statusEl.textContent = 'Bearer token required';
      statusEl.className = 'status err';
      return;
    }

    const fullPath = `/proxy?path=${encodeURIComponent(path)}${queryString ? '&' + queryString : ''}`;
    try {
      const resp = await fetch(fullPath, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      const data = await resp.json();
      const statusCode = data.status_code || resp.status;
      statusEl.textContent = `HTTP ${statusCode}`;
      statusEl.className = statusCode >= 200 && statusCode < 300 ? 'status ok' : 'status err';
      preEl.textContent = JSON.stringify(data.json !== undefined ? data.json : data, null, 2);
    } catch (err) {
      statusEl.textContent = 'Network error: ' + err.message;
      statusEl.className = 'status err';
      preEl.textContent = '';
    }
  }

  // init
  renderNav();
  renderEndpoint();
})();
</script>
</body>
</html>
"""

# ----------------------------------------------------------------------
# ROUTE: serve frontend
# ----------------------------------------------------------------------
@app.route("/")
def index():
    return render_template_string(INDEX_HTML)

# ----------------------------------------------------------------------
# MAIN
# ----------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
