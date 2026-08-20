import os
import time
import requests

# Set your variables
REPO_OWNER = "richa866"
REPO_NAME = "generatingIssues"

# Paste your Personal Access Token here (must have 'repo' scope)
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "YOUR_GITHUB_PERSONAL_ACCESS_TOKEN_HERE")

BASE_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}"
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "RepoGuardian-Seeder"
}

# -----------------------------------------------------------------------------
# REALISTIC DATASET (Duplicates, Regressions, Security, Contentious, etc.)
# -----------------------------------------------------------------------------
ISSUES_TO_SEED = [
    # --- 1. Duplicate Cluster A (Auth / Token Expiry) ---
    {
        "key": "auth_1",
        "title": "Background worker hits 401 Unauthorized after ~1 hour",
        "body": "We have `repoguardian monitor --daemon` running in a systemd unit.\nEvery hour, sync jobs fail with `[ERROR] HttpError: Bad credentials (HTTP 401)`.\nRestarting clears it temporarily, but JWT refresh token isn't being exchanged automatically.",
        "labels": ["bug", "auth"],
        "close": False,
        "comments": ["Investigating the Axios interceptor retry loop in `src/client/http.ts`."]
    },
    {
        "key": "auth_2",
        "title": "CLI daemon gets stuck in auth failure loop after running for 60m",
        "body": "Steps to reproduce:\n1. Run `repoguardian start --watch`\n2. Idle for 60 mins\n3. Daemon spams 401 errors.\nRequires manual restart.",
        "labels": ["bug", "cli"],
        "close": False,
        "comments": ["Likely duplicate of #{auth_1} — token lifecycle manager drops the bearer header during refresh exchange."]
    },
    {
        "key": "auth_3",
        "title": "OAuth token expired error in long-lived GitHub Actions runner",
        "body": "Our 75-minute matrix scan fails in later stages with: `RequestError: Expiration time claim ('exp') elapsed`. Does the CLI support automated token refresh?",
        "labels": ["auth"],
        "close": False,
        "comments": []
    },

    # --- 2. Duplicate Cluster B (YAML Boolean Parsing) ---
    {
        "key": "yaml_1",
        "title": "strict_mode: false in .guardianrc.yml is ignored",
        "body": "Setting `strict_mode: false` in configuration still fails the build on minor warnings. The parser loads unquoted string \"false\" which evaluates to truthy.",
        "labels": ["config", "bug"],
        "close": False,
        "comments": ["Confirmed. We need explicit boolean type coercion in YAML parser."]
    },
    {
        "key": "yaml_2",
        "title": "Cannot disable strict_mode from config file",
        "body": "Setting `strict_mode: false` has no effect. Only passing the CLI flag `--no-strict` works.",
        "labels": ["bug"],
        "close": False,
        "comments": ["Duplicate of #{yaml_1}."]
    },
    {
        "key": "yaml_3",
        "title": "Config parser treats boolean false as truthy",
        "body": "Any boolean setting configured as `false` in `.guardianrc` is treated as enabled.",
        "labels": ["config"],
        "close": False,
        "comments": []
    },

    # --- 3. Duplicate Cluster C (Monorepo Heap OOM Crash) ---
    {
        "key": "oom_1",
        "title": "FATAL ERROR: Ineffective mark-compacts near heap limit Allocation failed - JavaScript heap out of memory",
        "body": "Running `repoguardian scan --all` on a repo with ~25k commits crashes with Node heap exhaustion. The git log history is buffered in memory in a single array.",
        "labels": ["performance", "crash"],
        "close": False,
        "comments": ["Tracking this. We need to stream commit logs instead of buffering."]
    },
    {
        "key": "oom_2",
        "title": "Memory usage spikes to 4GB+ and process gets killed during initial indexing",
        "body": "On large repositories, the indexing worker consumes all available RAM within 3 minutes until Linux `oom-killer` terminates it.",
        "labels": ["performance"],
        "close": False,
        "comments": ["Workaround: pass `--depth 500` for now while streaming is implemented. See #{oom_1}."]
    },
    {
        "key": "oom_3",
        "title": "Heap out of memory error when running on repositories with long history",
        "body": "CI pipeline fails on repositories with >15k commits. Setting `NODE_OPTIONS=--max-old-space-size=8192` only delays the crash.",
        "labels": ["bug", "crash"],
        "close": False,
        "comments": []
    },

    # --- 4. Regression Pairs ---
    {
        "key": "regr_win_closed",
        "title": "Ignore patterns fail on Windows due to backslash path separators",
        "body": "On Windows 11, patterns in `.guardianignore` like `src/generated/**` do not match because resolver returns backslashes (`src\\generated\\file.ts`).",
        "labels": ["bug", "windows"],
        "close": True,
        "comments": ["Fixed in v2.3.1. We now normalize all paths to forward slashes before evaluating globs."]
    },
    {
        "key": "regr_win_open",
        "title": "Ignore patterns fail on Windows due to backslash path separators",
        "body": "On Windows 11, patterns in `.guardianignore` like `src/generated/**` do not match because resolver returns backslashes. Re-appeared in latest v2.4.0 release.",
        "labels": ["bug", "windows"],
        "close": False,
        "comments": ["Investigating regression — path normalization was bypassed during glob refactoring in PR #88."]
    },
    {
        "key": "regr_port_closed",
        "title": "`--port` argument is ignored when starting daemon via `repoguardian serve`",
        "body": "Passing `--port 8080` still binds to port 3000.",
        "labels": ["bug", "cli"],
        "close": True,
        "comments": ["Closed via PR #74. Mapped CLI commander flags to bootstrap options."]
    },
    {
        "key": "regr_port_open",
        "title": "`--port` argument is ignored when starting daemon via `repoguardian serve`",
        "body": "Passing `--port 8080` still binds to port 3000 in the latest version.",
        "labels": ["bug", "cli"],
        "close": False,
        "comments": []
    },

    # --- 5. Security Vulnerabilities ---
    {
        "key": "sec_traversal",
        "title": "Path traversal in report export endpoint via unvalidated download parameter",
        "body": "Endpoint `GET /api/reports/download?file=../../../../etc/passwd` allows reading arbitrary files outside storage directory. Requires `path.resolve` boundary verification.",
        "labels": ["security", "vulnerability"],
        "close": False,
        "comments": ["Escalated to core maintainers. Preparing emergency patch."]
    },
    {
        "key": "sec_sqli",
        "title": "SQL injection risk in custom database rule evaluator",
        "body": "In `src/rules/dbCheck.ts`, user queries are concatenated using string template interpolation for `order_by` instead of parameterized variables.",
        "labels": ["security"],
        "close": False,
        "comments": []
    },
    {
        "key": "sec_leak",
        "title": "Credential leak in CLI debug logs when running with `--verbose`",
        "body": "The authorization header `Bearer ghp_xxxx` is printed in plaintext to stdout and saved in CI log artifacts.",
        "labels": ["security", "cli"],
        "close": False,
        "comments": []
    },

    # --- 6. Contentious Debates ---
    {
        "key": "contentious_1",
        "title": "Drop CommonJS (CJS) support and ship pure ESM only in next minor release",
        "body": "Node 16 and 18 are reaching EOL. Supporting dual CJS/ESM builds causes hazards. Let's convert to `\"type\": \"module\"` in v2.5.",
        "labels": ["discussion", "breaking-change"],
        "close": False,
        "comments": [
            "**@enterprise-dev**: Please don't. This is a breaking change that will break CI across thousands of downstream projects.",
            "I disagree with doing this in a minor release. Violates semver. Closing as won't fix for v2.",
            "Not planned for v2 lifecycle. We will revisit in v3.0 planning."
        ]
      },

    # --- 7. Urgent / Missing Info ---
    {
        "key": "urg_1",
        "title": "Cannot compile project after updating to `@repoguardian/core@2.4.0` (Missing types)",
        "body": "Build fails with `error TS2304: Cannot find name 'RuleEngineContext'`. This is currently blocking our deployments.",
        "labels": ["bug", "typescript"],
        "close": False,
        "comments": []
    },
    {
        "key": "vague_1",
        "title": "it crashes with error",
        "body": "I ran the command and it gave error and broke. Please fix.",
        "labels": ["bug"],
        "close": False,
        "comments": []
    },

    # --- 8. Clean Control Group ---
    {
        "key": "clean_1",
        "title": "Add syntax highlighting for Rust snippets in HTML report output",
        "body": "### Feature Request\nAdd highlight.js/Prism grammar bundle for Rust code blocks in generated HTML reports.",
        "labels": ["enhancement"],
        "close": False,
        "comments": ["Makes sense! PRs welcome."]
    },
    {
        "key": "clean_2",
        "title": "Fix typo in `--help` output for `--max-concurrency` flag",
        "body": "Fixed spelling: 'concurrancy' -> 'concurrency'.",
        "labels": ["documentation"],
        "close": True,
        "comments": ["Merged, thank you!"]
    }
]

def main():
    print(f"Connecting to https://github.com/{REPO_OWNER}/{REPO_NAME}...")
    
    # 1. Test repository connection
    test_res = requests.get(BASE_URL, headers=HEADERS)
    if test_res.status_code != 200:
        print(f"Error accessing repo: HTTP {test_res.status_code}")
        print("Response:", test_res.text)
        print("\nPlease check that your GITHUB_TOKEN has 'repo' permissions and is valid.")
        return

    print("Authentication successful! Seeding issues...\n")
    id_map = {}

    # 2. Pass 1: Create all issues
    for idx, item in enumerate(ISSUES_TO_SEED, 1):
        res = requests.post(
            f"{BASE_URL}/issues",
            headers=HEADERS,
            json={
                "title": item["title"],
                "body": item["body"],
                "labels": item["labels"]
            }
        )
        if res.status_code == 201:
            num = res.json()["number"]
            id_map[item["key"]] = num
            print(f"[{idx}/{len(ISSUES_TO_SEED)}] Created Issue #{num}: {item['title'][:45]}...")
        else:
            print(f"Failed to create '{item['title']}': HTTP {res.status_code} - {res.text}")
        
        time.sleep(1.0)  # GitHub API rate limit pause

    # 3. Pass 2: Add comments and close resolved issues
    print("\nAdding discussion comments and closing resolved issues...")
    for item in ISSUES_TO_SEED:
        num = id_map.get(item["key"])
        if not num:
            continue

        for comment in item["comments"]:
            # Format dynamic cross-references like #{auth_1} -> #1
            formatted_comment = comment
            for k, mapped_num in id_map.items():
                formatted_comment = formatted_comment.replace(f"#{{{k}}}", f"#{mapped_num}")

            requests.post(
                f"{BASE_URL}/issues/{num}/comments",
                headers=HEADERS,
                json={"body": formatted_comment}
            )
            print(f"  └ Added comment to #{num}")
            time.sleep(1.0)

        if item["close"]:
            requests.patch(
                f"{BASE_URL}/issues/{num}",
                headers=HEADERS,
                json={"state": "closed"}
            )
            print(f"  └ Closed Issue #{num}")
            time.sleep(1.0)

    print("\nDone! Refresh your GitHub page:")
    print(f"https://github.com/{REPO_OWNER}/{REPO_NAME}/issues")

if __name__ == "__main__":
    main()