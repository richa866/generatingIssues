#!/usr/bin/env python3
import os
import time
from typing import Dict, List, Any
import requests
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

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
# SEEDING ENGINE
# -----------------------------------------------------------------------------

class SeedRequest(BaseModel):
    owner: str
    repo: str
    token: str
    category: str  # 'all', 'duplicates', 'regressions', 'security', 'contentious', 'controls'
    dry_run: bool = False

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
        raise HTTPException(status_code=400, detail="Invalid category specified.")

    if dry_run:
        logs.append(f"[DRY-RUN] Simulating issue creation for target repository {owner}/{repo} (Category: {category})")
        logs.append(f"[DRY-RUN] Total templates queued: {len(items_to_seed)}")
        
        simulated_id_map: Dict[str, int] = {}
        sim_issue_counter = 101

        # Pass 1 Simulation
        for item in items_to_seed:
            simulated_id_map[item["id_key"]] = sim_issue_counter
            logs.append(f"[DRY-RUN] Would create Issue #{sim_issue_counter}: '{item['title']}' (Labels: {item['labels']})")
            sim_issue_counter += 1

        # Pass 2 Simulation
        for item in items_to_seed:
            num = simulated_id_map[item["id_key"]]
            for comment in item["comments"]:
                formatted_comment = comment
                for k, mapped_num in simulated_id_map.items():
                    formatted_comment = formatted_comment.replace(f"{{{k}}}", str(mapped_num))
                logs.append(f"  └ [DRY-RUN] Would add comment to #{num}: '{formatted_comment[:60]}...'")
            if item["should_close"]:
                logs.append(f"  └ [DRY-RUN] Would close Issue #{num}")
        
        logs.append("[DRY-RUN] Simulation finished. No GitHub API calls were dispatched.")
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
            "labels": item["labels"]
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
        for comment in item["comments"]:
            # Format dynamic cross-references
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
        if item["should_close"]:
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
# API & FRONTEND
# -----------------------------------------------------------------------------

@app.get("/api/health")
def health_check():
    total_issues = sum(len(items) for items in DATA_STORE.values())
    return {
        "status": "healthy",
        "service": "RepoGuardian Test Suite Controller",
        "version": "1.1.0",
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

@app.post("/api/seed")
def seed_endpoint(req: SeedRequest):
    try:
        logs = execute_seeding(req.owner, req.repo, req.token, req.category, dry_run=req.dry_run)
        return {"status": "success", "dry_run": req.dry_run, "logs": logs}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
def index_page():
    return """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>RepoGuardian Demo Suite Generator</title>
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen py-10 px-4 flex flex-col items-center">
  <div class="max-w-4xl w-full">
    <!-- Header -->
    <div class="mb-8 text-center">
      <div class="inline-flex items-center gap-2 px-3 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 rounded-full text-xs font-mono mb-3">
        ● LIVE GITHUB REST ENGINE
      </div>
      <h1 class="text-3xl font-extrabold tracking-tight">RepoGuardian Demo Seeder</h1>
      <p class="text-slate-400 text-sm mt-1">Generate realistic signals directly into a live GitHub repo for tool demonstrations.</p>
    </div>

    <!-- Credentials Card -->
    <div class="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-6 shadow-xl">
      <h2 class="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4">Target Repository Configuration</h2>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
        <div>
          <label class="block text-xs font-medium text-slate-400 mb-1">GitHub Owner / Org</label>
          <input id="owner" type="text" placeholder="e.g. your-username" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-indigo-500">
        </div>
        <div>
          <label class="block text-xs font-medium text-slate-400 mb-1">Repository Name</label>
          <input id="repo" type="text" placeholder="e.g. repoguardian-demo" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-indigo-500">
        </div>
        <div>
          <label class="block text-xs font-medium text-slate-400 mb-1">Personal Access Token (repo scope)</label>
          <input id="token" type="password" placeholder="ghp_xxxxxxxxxxxx" class="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm focus:outline-none focus:border-indigo-500">
        </div>
      </div>
      
      <div class="flex items-center justify-between pt-3 border-t border-slate-800/80">
        <label class="flex items-center gap-2 cursor-pointer text-xs text-slate-300 hover:text-white select-none">
          <input id="dryRun" type="checkbox" class="rounded bg-slate-950 border-slate-700 text-indigo-600 focus:ring-0 focus:ring-offset-0">
          <span>Dry Run Mode (Simulate without creating actual GitHub issues)</span>
        </label>
        <span class="text-[11px] text-slate-500 font-mono" id="healthStats">API Status: Ready</span>
      </div>
    </div>

    <!-- Action Buttons -->
    <div class="bg-slate-900 border border-slate-800 rounded-xl p-6 mb-6 shadow-xl">
      <h2 class="text-sm font-semibold text-slate-300 uppercase tracking-wider mb-4">Inject Test Scenarios</h2>
      <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-6 gap-3">
        <button onclick="triggerSeed('all')" class="bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs py-2.5 px-3 rounded-lg transition-all shadow-md active:scale-95 col-span-2 sm:col-span-3 md:col-span-1">
          🚀 Seed All Data
        </button>
        <button onclick="triggerSeed('duplicates')" class="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-medium text-xs py-2.5 px-3 rounded-lg transition-all active:scale-95">
          👯 Duplicates
        </button>
        <button onclick="triggerSeed('regressions')" class="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-medium text-xs py-2.5 px-3 rounded-lg transition-all active:scale-95">
          🔁 Regressions
        </button>
        <button onclick="triggerSeed('security')" class="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-medium text-xs py-2.5 px-3 rounded-lg transition-all active:scale-95">
          🔒 Security
        </button>
        <button onclick="triggerSeed('contentious')" class="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-medium text-xs py-2.5 px-3 rounded-lg transition-all active:scale-95">
          🔥 Contentious
        </button>
        <button onclick="triggerSeed('controls')" class="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-medium text-xs py-2.5 px-3 rounded-lg transition-all active:scale-95">
          ✅ Controls
        </button>
      </div>
    </div>

    <!-- Live Execution Logs -->
    <div class="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
      <div class="flex items-center justify-between mb-3">
        <h2 class="text-sm font-semibold text-slate-300 uppercase tracking-wider">Live Activity Log</h2>
        <span id="statusIndicator" class="text-xs text-slate-500 font-mono">Idle</span>
      </div>
      <div id="logConsole" class="bg-slate-950 border border-slate-800/80 rounded-lg p-4 font-mono text-xs text-emerald-400 h-64 overflow-y-auto space-y-1">
        <div class="text-slate-600">// Output from GitHub REST operations will stream here...</div>
      </div>
    </div>
  </div>

  <script>
    // Autofill token/repo from URL or LocalStorage if present
    window.addEventListener('DOMContentLoaded', async () => {
      document.getElementById('owner').value = localStorage.getItem('rg_owner') || '';
      document.getElementById('repo').value = localStorage.getItem('rg_repo') || '';
      document.getElementById('token').value = localStorage.getItem('rg_token') || '';

      try {
        const res = await fetch('/api/health');
        if (res.ok) {
          const data = await res.json();
          document.getElementById('healthStats').innerText = `v${data.version} · ${data.total_seed_templates} test templates ready`;
        }
      } catch (e) {
        // ignore offline preview
      }
    });

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

      // Persist in local storage
      localStorage.setItem('rg_owner', owner);
      localStorage.setItem('rg_repo', repo);
      if (token) localStorage.setItem('rg_token', token);

      // UI state updates
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