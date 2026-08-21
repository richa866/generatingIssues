#!/usr/bin/env python3
import csv
import io
import json
import os
import time
from typing import Dict, List, Any, Optional, Union
import requests
from fastapi import FastAPI, HTTPException, Response, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

app = FastAPI(title="RepoGuardian Test Suite Controller")

BASE_URL = "https://api.github.com"
SLEEP_INTERVAL = 1.0

# -----------------------------------------------------------------------------
# ISSUE DATA DEFINITIONS
# -----------------------------------------------------------------------------

DATA_STORE: Dict[str, List[Dict[str, Any]]] = {
    "duplicates": [
        {
            "id_key": "dup_auth_1",
            "title": "Background worker hits 401 Unauthorized after ~1 hour",
            "body": "We have `repoguardian monitor --daemon` running in a systemd service.\n\nEvery hour, jobs fail with:\n```text\n[ERROR] HttpError: Bad credentials (HTTP 401)\n```\nRestarting clears it. JWT refresh token isn't being exchanged automatically.",
            "labels": ["bug", "auth"],
            "should_close": False,
            "comments": ["Investigating Axios token interceptor retry loop."]
        },
        {
            "id_key": "dup_auth_2",
            "title": "CLI daemon gets stuck in auth failure loop after running for 60m",
            "body": "Steps:\n1. `repoguardian start --watch`\n2. Idle for 60 mins\n3. Throws 401 continuously.\n\nRequires manual restart.",
            "labels": ["bug", "cli"],
            "should_close": False,
            "comments": ["Likely duplicate of #{dup_auth_1} — token lifecycle manager drops the authorization header."]
        },
        {
            "id_key": "dup_auth_3",
            "title": "OAuth token expired error in long-lived GitHub Actions runner",
            "body": "Our 75-minute matrix scan fails in later stages with: `RequestError: Expiration time claim ('exp') elapsed`. Does the CLI handle auto-refresh?",
            "labels": ["auth"],
            "should_close": False,
            "comments": []
        },
        {
            "id_key": "dup_yaml_1",
            "title": "strict_mode: false in .guardianrc.yml is ignored",
            "body": "Setting `strict_mode: false` still fails on minor warnings. Parser evaluates unquoted YAML string as truthy.",
            "labels": ["config", "bug"],
            "should_close": False,
            "comments": ["Confirmed. Need boolean casting in YAML parser loader."]
        },
        {
            "id_key": "dup_yaml_2",
            "title": "Cannot disable strict_mode from config file",
            "body": "Setting `strict_mode: false` has no effect. Only CLI flag `--no-strict` works.",
            "labels": ["bug"],
            "should_close": False,
            "comments": ["Duplicate of #{dup_yaml_1}."]
        },
        {
            "id_key": "dup_yaml_3",
            "title": "Config parser treats boolean false as truthy",
            "body": "Any boolean option set to `false` in `.guardianrc` is treated as enabled.",
            "labels": ["config"],
            "should_close": False,
            "comments": []
        }
    ],
    "regressions": [
        {
            "id_key": "regr_win_closed",
            "title": "Ignore patterns fail on Windows due to backslash path separators",
            "body": "Path matcher fails on Windows (`src\\app\\file.ts`) when evaluating `.guardianignore`.",
            "labels": ["bug", "windows"],
            "should_close": True,
            "comments": ["Fixed in v2.3.1. Normalized glob paths to forward slashes."]
        },
        {
            "id_key": "regr_win_open",
            "title": "Ignore patterns fail on Windows due to backslash path separators",
            "body": "Path matcher fails on Windows (`src\\app\\file.ts`) when evaluating `.guardianignore` in v2.4.0.",
            "labels": ["bug", "windows"],
            "should_close": False,
            "comments": ["Investigating regression introduced in glob refactor #88."]
        },
        {
            "id_key": "regr_port_closed",
            "title": "`--port` argument is ignored when starting daemon via `repoguardian serve`",
            "body": "Passing `--port 8080` still binds to port 3000.",
            "labels": ["bug", "cli"],
            "should_close": True,
            "comments": ["Closed via #74. Mapped CLI commander flags to config."]
        },
        {
            "id_key": "regr_port_open",
            "title": "`--port` argument is ignored when starting daemon via `repoguardian serve`",
            "body": "Passing `--port 8080` still binds to port 3000 in the latest release.",
            "labels": ["bug", "cli"],
            "should_close": False,
            "comments": []
        }
    ],
    "security": [
        {
            "id_key": "sec_path_traversal",
            "title": "Path traversal in report exporter via unvalidated download parameter",
            "body": "Endpoint `GET /api/reports/download?file=../../../../etc/passwd` allows downloading files outside storage directory.",
            "labels": ["security", "vulnerability"],
            "should_close": False,
            "comments": ["Escalated to maintainers. Restricting resolution to STORAGE_DIR sandbox."]
        },
        {
            "id_key": "sec_sql_injection",
            "title": "SQL injection risk in custom database rule evaluator",
            "body": "Query fragments use raw string interpolation for `order_by` instead of parameterized variables.",
            "labels": ["security"],
            "should_close": False,
            "comments": []
        },
        {
            "id_key": "sec_credential_leak",
            "title": "Credential leak in CLI debug logs when running with `--verbose`",
            "body": "The authorization header `Bearer ghp_xxxx` is dumped in plaintext to standard output in CI logs.",
            "labels": ["security", "cli"],
            "should_close": False,
            "comments": []
        }
    ],
    "contentious": [
        {
            "id_key": "contentious_esm",
            "title": "Drop CommonJS (CJS) support and ship pure ESM only in next minor release",
            "body": "Node 16/18 are EOL. Convert the package to `\"type\": \"module\"` in v2.5.",
            "labels": ["discussion", "breaking-change"],
            "should_close": False,
            "comments": [
                "**@enterprise-user**: Please don't. This will break Jest CI suites across thousands of repos.",
                "I disagree with doing this in a minor version. This is a breaking change and violates semver.",
                "**@contributor**: Most modern libraries migrated to pure ESM already.",
                "There is huge pushback on this. We won't be able to upgrade.",
                "Closing as won't fix for v2. We'll revisit this in v3.0 roadmap planning."
            ]
        }
    ],
    "controls": [
        {
            "id_key": "ctrl_1",
            "title": "Add syntax highlighting for Rust snippets in HTML report",
            "body": "### Feature Request\nAdd Rust Prism/highlight.js grammar bundle to HTML report template.",
            "labels": ["enhancement"],
            "should_close": False,
            "comments": ["Good suggestion. PR welcome!"]
        },
        {
            "id_key": "ctrl_2_closed",
            "title": "Fix typo in `--help` output for `--max-concurrency`",
            "body": "Fixed spelling: 'concurrancy' -> 'concurrency'.",
            "labels": ["documentation"],
            "should_close": True,
            "comments": ["Merged, thank you for the fix!"]
        }
    ]
}

# -----------------------------------------------------------------------------
# PYDANTIC SCHEMAS
# -----------------------------------------------------------------------------

class SeedRequest(BaseModel):
    owner: str
    repo: str
    token: str
    category: str  # 'all' or category key
    dry_run: bool = False

class TemplateItem(BaseModel):
    id_key: str
    title: str
    body: str = ""
    labels: List[str] = Field(default_factory=list)
    should_close: bool = False
    comments: List[str] = Field(default_factory=list)

class ImportRequest(BaseModel):
    category: Optional[str] = "custom"
    items: Optional[List[TemplateItem]] = None
    bundle: Optional[Dict[str, List[TemplateItem]]] = None

# -----------------------------------------------------------------------------
# SEEDING ENGINE
# -----------------------------------------------------------------------------

def execute_seeding(owner: str, repo: str, token: str, category: str, dry_run: bool = False) -> List[str]:
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "RepoGuardian-Dashboard"
    }
    
    logs = []
    
    # Collect requested issues
    items_to_seed = []
    if category == "all":
        for cat_items in DATA_STORE.values():
            items_to_seed.extend(cat_items)
    elif category in DATA_STORE:
        items_to_seed.extend(DATA_STORE[category])
    else:
        raise HTTPException(status_code=400, detail=f"Invalid category '{category}' specified.")

    if dry_run:
        logs.append(f"[DRY-RUN] Simulating issue creation for repository {owner}/{repo} (Category: {category})")
        logs.append(f"[DRY-RUN] Total templates queued: {len(items_to_seed)}")
        
        simulated_id_map: Dict[str, int] = {}
        sim_issue_counter = 101

        # Pass 1 Simulation
        for item in items_to_seed:
            simulated_id_map[item["id_key"]] = sim_issue_counter
            logs.append(f"[DRY-RUN] Would create Issue #{sim_issue_counter}: '{item['title']}' (Labels: {item.get('labels', [])})")
            sim_issue_counter += 1

        # Pass 2 Simulation
        for item in items_to_seed:
            num = simulated_id_map[item["id_key"]]
            for comment in item.get("comments", []):
                formatted_comment = comment
                for k, mapped_num in simulated_id_map.items():
                    formatted_comment = formatted_comment.replace(f"{{{k}}}", str(mapped_num))
                logs.append(f"  └ [DRY-RUN] Would add comment to #{num}: '{formatted_comment[:60]}...'")
            if item.get("should_close", False):
                logs.append(f"  └ [DRY-RUN] Would close Issue #{num}")
        
        logs.append("[DRY-RUN] Simulation completed successfully. No remote GitHub calls were made.")
        return logs

    # Pre-flight repo test
    test_res = requests.get(f"{BASE_URL}/repos/{owner}/{repo}", headers=headers)
    if test_res.status_code != 200:
        raise HTTPException(status_code=400, detail=f"GitHub API Error: {test_res.text}")

    id_to_number: Dict[str, int] = {}

    # Pass 1: Create Issues
    for item in items_to_seed:
        payload = {
            "title": item["title"],
            "body": item["body"],
            "labels": item.get("labels", [])
        }
        res = requests.post(f"{BASE_URL}/repos/{owner}/{repo}/issues", headers=headers, json=payload)
        if res.status_code == 201:
            num = res.json()["number"]
            id_to_number[item["id_key"]] = num
            logs.append(f"Created Issue #{num}: {item['title'][:40]}...")
        else:
            logs.append(f"Failed creating '{item['title']}': HTTP {res.status_code}")
        time.sleep(SLEEP_INTERVAL)

    # Pass 2: Comments & Closures
    for item in items_to_seed:
        if item["id_key"] not in id_to_number:
            continue
        num = id_to_number[item["id_key"]]

        # Post comments
        for comment in item.get("comments", []):
            formatted_comment = comment
            for k, mapped_num in id_to_number.items():
                formatted_comment = formatted_comment.replace(f"{{{k}}}", str(mapped_num))
            
            c_res = requests.post(
                f"{BASE_URL}/repos/{owner}/{repo}/issues/{num}/comments",
                headers=headers,
                json={"body": formatted_comment}
            )
            if c_res.status_code == 201:
                logs.append(f"  └ Added comment to #{num}")
            time.sleep(SLEEP_INTERVAL)

        # Patch close state if required
        if item.get("should_close", False):
            p_res = requests.patch(
                f"{BASE_URL}/repos/{owner}/{repo}/issues/{num}",
                headers=headers,
                json={"state": "closed"}
            )
            if p_res.status_code == 200:
                logs.append(f"  └ Closed Issue #{num}")
            time.sleep(SLEEP_INTERVAL)

    return logs

# -----------------------------------------------------------------------------
# API ENDPOINTS
# -----------------------------------------------------------------------------

@app.get("/api/health")
def health_check():
    total_issues = sum(len(items) for items in DATA_STORE.values())
    return {
        "status": "healthy",
        "service": "RepoGuardian Test Suite Controller",
        "version": "1.2.0",
        "categories": list(DATA_STORE.keys()),
        "total_seed_templates": total_issues
    }

@app.get("/api/categories")
def get_categories():
    return {
        cat: {
            "count": len(items),
            "sample_titles": [item["title"] for item in items[:2]]
        }
        for cat, items in DATA_STORE.items()
    }

@app.get("/api/export")
def export_templates(
    format: str = Query("json", pattern="^(json|csv)$"),
    category: Optional[str] = "all"
):
    """
    Export current issue templates in JSON or CSV format.
    """
    export_data: Dict[str, List[Dict[str, Any]]] = {}
    if category == "all":
        export_data = DATA_STORE
    elif category in DATA_STORE:
        export_data = {category: DATA_STORE[category]}
    else:
        raise HTTPException(status_code=404, detail=f"Category '{category}' not found.")

    if format == "json":
        content = json.dumps(export_data, indent=2)
        filename = f"repoguardian_templates_{category}.json"
        return Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    
    # CSV format export
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["category", "id_key", "title", "body", "labels", "should_close", "comments"])
    
    for cat_name, items in export_data.items():
        for it in items:
            writer.writerow([
                cat_name,
                it.get("id_key", ""),
                it.get("title", ""),
                it.get("body", ""),
                ";".join(it.get("labels", [])),
                "true" if it.get("should_close", False) else "false",
                " || ".join(it.get("comments", []))
            ])
    
    csv_content = output.getvalue()
    filename = f"repoguardian_templates_{category}.csv"
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@app.post("/api/import")
def import_templates(req: ImportRequest):
    """
    Import custom templates into DATA_STORE as a new or updated category.
    """
    imported_count = 0
    categories_affected = []

    if req.bundle:
        for cat_name, items in req.bundle.items():
            clean_cat = cat_name.strip().lower()
            if not clean_cat:
                continue
            item_dicts = [it.model_dump() for it in items]
            DATA_STORE[clean_cat] = item_dicts
            imported_count += len(item_dicts)
            categories_affected.append(clean_cat)
    elif req.items:
        clean_cat = (req.category or "custom").strip().lower()
        item_dicts = [it.model_dump() for it in req.items]
        if clean_cat in DATA_STORE:
            # Append non-duplicate keys or overwrite
            existing_keys = {it["id_key"] for it in DATA_STORE[clean_cat]}
            new_items = [it for it in item_dicts if it["id_key"] not in existing_keys]
            DATA_STORE[clean_cat].extend(new_items)
            imported_count = len(new_items)
        else:
            DATA_STORE[clean_cat] = item_dicts
            imported_count = len(item_dicts)
        categories_affected.append(clean_cat)
    else:
        raise HTTPException(status_code=400, detail="Provide either 'items' with 'category' or a 'bundle' mapping.")

    return {
        "status": "success",
        "message": f"Successfully imported {imported_count} template(s).",
        "categories_affected": categories_affected,
        "total_categories": len(DATA_STORE)
    }

@app.post("/api/seed")
def seed_endpoint(req: SeedRequest):
    try:
        logs = execute_seeding(req.owner, req.repo, req.token, req.category, dry_run=req.dry_run)
        return {"status": "success", "dry_run": req.dry_run, "logs": logs}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -----------------------------------------------------------------------------
# FRONTEND UI
# -----------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def index_page():
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>RepoGuardian Demo Suite Generator</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen py-8 px-4 flex flex-col items-center selection:bg-indigo-500 selection:text-white">
  <div class="max-w-5xl w-full">
    
    <!-- Top Header -->
    <div class="mb-8 flex flex-col sm:flex-row items-center justify-between gap-4 pb-6 border-b border-slate-800/80">
      <div>
        <div class="inline-flex items-center gap-2 px-3 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full text-xs font-mono mb-2">
          ● LIVE GITHUB REST ENGINE v1.2.0
        </div>
        <h1 class="text-3xl font-extrabold tracking-tight text-white">RepoGuardian Demo Seeder</h1>
        <p class="text-slate-400 text-sm mt-1">Inject realistic GitHub issues, discussions, and regressions with backup & custom template support.</p>
      </div>

      <!-- Quick Actions (Export / Import) -->
      <div class="flex items-center gap-2">
        <div class="relative inline-block text-left">
          <button id="exportDropdownBtn" onclick="toggleExportMenu()" class="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-medium text-xs py-2 px-3.5 rounded-lg flex items-center gap-1.5 transition-all shadow">
            <span>📥 Export Templates</span>
            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
          </button>
          <div id="exportMenu" class="hidden absolute right-0 mt-2 w-44 bg-slate-900 border border-slate-800 rounded-lg shadow-2xl py-1 z-20">
            <a href="/api/export?format=json" download class="block px-4 py-2 text-xs text-slate-300 hover:bg-slate-800 hover:text-white">Export as JSON</a>
            <a href="/api/export?format=csv" download class="block px-4 py-2 text-xs text-slate-300 hover:bg-slate-800 hover:text-white">Export as CSV</a>
          </div>
        </div>

        <button onclick="openImportModal()" class="bg-indigo-600/90 hover:bg-indigo-600 text-white font-medium text-xs py-2 px-3.5 rounded-lg flex items-center gap-1.5 transition-all shadow-md active:scale-95">
          <span>📤 Import Custom</span>
        </button>
      </div>
    </div>

    <!-- Target Repository Configuration -->
    <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-6 mb-6 shadow-xl backdrop-blur">
      <h2 class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4 flex items-center gap-2">
        <svg class="w-4 h-4 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path></svg>
        Target GitHub Repository
      </h2>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
        <div>
          <label class="block text-xs font-medium text-slate-400 mb-1">GitHub Owner / Org</label>
          <input id="owner" type="text" placeholder="e.g. your-username" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500 transition">
        </div>
        <div>
          <label class="block text-xs font-medium text-slate-400 mb-1">Repository Name</label>
          <input id="repo" type="text" placeholder="e.g. repoguardian-demo" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500 transition">
        </div>
        <div>
          <label class="block text-xs font-medium text-slate-400 mb-1">Personal Access Token (repo scope)</label>
          <input id="token" type="password" placeholder="ghp_xxxxxxxxxxxx" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:outline-none focus:border-indigo-500 transition">
        </div>
      </div>
      
      <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-3 border-t border-slate-800/80">
        <label class="flex items-center gap-2 cursor-pointer text-xs text-slate-300 hover:text-white select-none">
          <input id="dryRun" type="checkbox" class="rounded bg-slate-950 border-slate-700 text-indigo-600 focus:ring-0 focus:ring-offset-0">
          <span>Dry Run Mode (Simulate execution without modifying GitHub)</span>
        </label>
        <span class="text-[11px] text-slate-500 font-mono" id="healthStats">API Status: Initializing...</span>
      </div>
    </div>

    <!-- Scenarios Grid -->
    <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-6 mb-6 shadow-xl">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
          <svg class="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
          Inject Test Scenarios
        </h2>
        <span class="text-xs text-slate-500" id="categoryCountBadge">Loading scenarios...</span>
      </div>

      <!-- Categories Container (Populated Dynamically) -->
      <div id="categoryGrid" class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
        <!-- Injected by JavaScript -->
      </div>
    </div>

    <!-- Live Execution Logs -->
    <div class="bg-slate-900/90 border border-slate-800 rounded-xl p-6 shadow-xl">
      <div class="flex items-center justify-between mb-3">
        <h2 class="text-xs font-bold text-slate-400 uppercase tracking-wider">Live Activity Log</h2>
        <div class="flex items-center gap-3">
          <button onclick="clearLogs()" class="text-slate-500 hover:text-slate-400 text-xs">Clear</button>
          <span id="statusIndicator" class="text-xs text-slate-500 font-mono">Idle</span>
        </div>
      </div>
      <div id="logConsole" class="bg-slate-950 border border-slate-800/80 rounded-lg p-4 font-mono text-xs text-emerald-400 h-64 overflow-y-auto space-y-1">
        <div class="text-slate-600">// Realtime GitHub REST operations will stream here...</div>
      </div>
    </div>

  </div>

  <!-- Modal for Custom Template Import -->
  <div id="importModal" class="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center hidden p-4">
    <div class="bg-slate-900 border border-slate-800 rounded-xl max-w-2xl w-full p-6 shadow-2xl relative">
      <div class="flex items-center justify-between mb-4 pb-3 border-b border-slate-800">
        <div>
          <h3 class="text-base font-bold text-white">Import Custom Issue Templates</h3>
          <p class="text-xs text-slate-400 mt-0.5">Upload a JSON bundle or paste template definitions below.</p>
        </div>
        <button onclick="closeImportModal()" class="text-slate-400 hover:text-white text-lg font-mono">✕</button>
      </div>

      <div class="space-y-4">
        <div>
          <label class="block text-xs font-medium text-slate-300 mb-1">Target Category Name</label>
          <input id="importCategoryName" type="text" value="custom_pack" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-indigo-500">
        </div>

        <div>
          <div class="flex items-center justify-between mb-1">
            <label class="block text-xs font-medium text-slate-300">Template JSON Definition</label>
            <button onclick="loadSampleTemplate()" class="text-[11px] text-indigo-400 hover:text-indigo-300">Load Sample JSON</button>
          </div>
          <textarea id="importJsonText" rows="9" placeholder="Paste JSON template array or bundle object here..." class="w-full bg-slate-950 border border-slate-800 rounded-lg p-3 font-mono text-xs text-slate-200 focus:outline-none focus:border-indigo-500"></textarea>
        </div>

        <div class="flex items-center justify-between pt-2">
          <input type="file" id="jsonFileInput" accept=".json" class="text-xs text-slate-400 file:mr-2 file:py-1 file:px-2.5 file:rounded file:border-0 file:text-xs file:bg-slate-800 file:text-slate-200 hover:file:bg-slate-700 cursor-pointer">
          <div class="flex items-center gap-2">
            <button onclick="closeImportModal()" class="px-3 py-1.5 text-xs text-slate-400 hover:text-slate-200">Cancel</button>
            <button onclick="submitImport()" class="bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs px-4 py-1.5 rounded-lg shadow transition-all">Import Templates</button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <script>
    window.addEventListener('DOMContentLoaded', async () => {
      document.getElementById('owner').value = localStorage.getItem('rg_owner') || '';
      document.getElementById('repo').value = localStorage.getItem('rg_repo') || '';
      document.getElementById('token').value = localStorage.getItem('rg_token') || '';

      await refreshCategories();

      // Handle JSON file picker
      document.getElementById('jsonFileInput').addEventListener('change', function(e) {
        const file = e.target.files[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = function(evt) {
          document.getElementById('importJsonText').value = evt.target.result;
        };
        reader.readAsText(file);
      });
    });

    function toggleExportMenu() {
      const menu = document.getElementById('exportMenu');
      menu.classList.toggle('hidden');
    }

    document.addEventListener('click', (e) => {
      const btn = document.getElementById('exportDropdownBtn');
      const menu = document.getElementById('exportMenu');
      if (btn && menu && !btn.contains(e.target) && !menu.contains(e.target)) {
        menu.classList.add('hidden');
      }
    });

    function openImportModal() {
      document.getElementById('importModal').classList.remove('hidden');
    }

    function closeImportModal() {
      document.getElementById('importModal').classList.add('hidden');
    }

    function loadSampleTemplate() {
      const sample = [
        {
          "id_key": "custom_sample_1",
          "title": "Custom Test: High Memory Consumption under heavy concurrent workload",
          "body": "Running 50 parallel requests causes memory to exceed 2GB.\n\nReproduction:\n```bash\nrepoguardian bench --concurrency 50\n```",
          "labels": ["performance", "custom"],
          "should_close": false,
          "comments": ["Profile with heapdump to pinpoint leak."]
        }
      ];
      document.getElementById('importJsonText').value = JSON.stringify(sample, null, 2);
    }

    async function refreshCategories() {
      try {
        const res = await fetch('/api/categories');
        if (!res.ok) return;
        const categories = await res.json();

        const grid = document.getElementById('categoryGrid');
        grid.innerHTML = `
          <button onclick="triggerSeed('all')" class="bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs py-2.5 px-3 rounded-lg transition-all shadow-md active:scale-95 col-span-2 sm:col-span-3 md:col-span-1">
            🚀 Seed All
          </button>
        `;

        let total = 0;
        for (const [key, data] of Object.entries(categories)) {
          total += data.count;
          const label = key.charAt(0).toUpperCase() + key.slice(1);
          grid.innerHTML += `
            <button onclick="triggerSeed('${key}')" class="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-medium text-xs py-2.5 px-3 rounded-lg transition-all active:scale-95 flex flex-col items-center justify-center text-center">
              <span>${label}</span>
              <span class="text-[10px] text-slate-400 mt-0.5">${data.count} items</span>
            </button>
          `;
        }

        document.getElementById('categoryCountBadge').innerText = `${Object.keys(categories).length} categories · ${total} templates`;
        document.getElementById('healthStats').innerText = `API Ready · ${total} total templates available`;
      } catch (e) {
        console.error("Failed loading categories", e);
      }
    }

    async function submitImport() {
      const catName = document.getElementById('importCategoryName').value.trim() || 'custom';
      const rawJson = document.getElementById('importJsonText').value.trim();

      if (!rawJson) {
        alert('Please paste valid JSON or choose a JSON file.');
        return;
      }

      let parsed;
      try {
        parsed = JSON.parse(rawJson);
      } catch (e) {
        alert('Invalid JSON syntax: ' + e.message);
        return;
      }

      let payload = {};
      if (Array.isArray(parsed)) {
        payload = { category: catName, items: parsed };
      } else if (typeof parsed === 'object') {
        payload = { bundle: parsed };
      }

      try {
        const res = await fetch('/api/import', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        });
        const result = await res.json();
        if (!res.ok) throw new Error(result.detail || 'Import failed');

        alert('Success: ' + result.message);
        closeImportModal();
        await refreshCategories();
      } catch (err) {
        alert('Import Error: ' + err.message);
      }
    }

    function clearLogs() {
      document.getElementById('logConsole').innerHTML = `<div class="text-slate-600">// Log cleared.</div>`;
    }

    async function triggerSeed(category) {
      const owner = document.getElementById('owner').value.trim();
      const repo = document.getElementById('repo').value.trim();
      const token = document.getElementById('token').value.trim();
      const dryRun = document.getElementById('dryRun').checked;
      const consoleBox = document.getElementById('logConsole');
      const statusIndicator = document.getElementById('statusIndicator');

      if (!owner || !repo || (!dryRun && !token)) {
        alert('Please fill in GitHub Owner and Repo Name (and Token if not in Dry Run mode).');
        return;
      }

      localStorage.setItem('rg_owner', owner);
      localStorage.setItem('rg_repo', repo);
      if (token) localStorage.setItem('rg_token', token);

      const actionLabel = dryRun ? `[DRY-RUN] Simulating` : `Seeding`;
      statusIndicator.innerText = `${actionLabel} [${category}]...`;
      statusIndicator.className = "text-xs text-amber-400 font-mono animate-pulse";
      consoleBox.innerHTML += `<div class="text-amber-300 mt-2">=== ${actionLabel} category: ${category} ===</div>`;

      try {
        const res = await fetch('/api/seed', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ owner, repo, token: token || 'mock_token', category, dry_run: dryRun })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || 'Failed');

        data.logs.forEach(line => {
          consoleBox.innerHTML += `<div>${line}</div>`;
        });
        consoleBox.innerHTML += `<div class="text-emerald-400 font-bold mt-1">✔ Finished successfully.</div>`;
        statusIndicator.innerText = dryRun ? "Simulation Done" : "Completed";
        statusIndicator.className = "text-xs text-emerald-400 font-mono";
      } catch (err) {
        consoleBox.innerHTML += `<div class="text-rose-400 font-bold mt-1">✖ Error: ${err.message}</div>`;
        statusIndicator.innerText = "Failed";
        statusIndicator.className = "text-xs text-rose-400 font-mono";
      }
      consoleBox.scrollTop = consoleBox.scrollHeight;
    }
  </script>
</body>
</html>
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)