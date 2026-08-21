# RepoGuardian Issue Seeder & Test Suite Controller

A FastAPI-powered live test harness and seeder for GitHub repositories. Inject realistic signals (duplicates, regressions, security flaws, contentious discussions, control issues, or custom test templates) into any target GitHub repository for end-to-end demonstrations and triage validation.

---

## Features

- 🚀 **Live GitHub REST API Seeding**: Automatically creates issues, handles comment threading, references issue IDs dynamically across comments, and simulates closure workflows.
- 🧪 **Dry-Run Simulation**: Test scenarios and inspect generated logs without sending requests to GitHub.
- 📥 **Export Templates (JSON & CSV)**: Export all or specific template categories for backups, auditing, or sharing.
- 📤 **Import Custom Templates**: Dynamically upload JSON bundles or custom issue lists with live UI registration.
- 📊 **Dynamic Scenario Dashboard**: Interactive web UI with real-time log streaming and instant category updates.
- 🩺 **Health & Category Inspection**: REST endpoints for telemetry and scenario metrics.

---

## Installation & Setup

### 1. Requirements

Ensure Python 3.9+ is installed. Install dependencies:

```bash
pip install -r requirements.txt
```

### 2. Run Local Server

Start the application using Uvicorn:

```bash
uvicorn app:app --reload --port 8000
```

Access the web interface at **`http://localhost:8000`**.

---

## API Reference

### Health & Metadata
- **`GET /api/health`**: Returns service status, version, category breakdown, and total template counts.
- **`GET /api/categories`**: Returns available scenario categories and sample item titles.

### Seeding
- **`POST /api/seed`**: Dispatches issue generation to GitHub REST API.
  ```json
  {
    "owner": "username",
    "repo": "repository-name",
    "token": "ghp_xxxxxxxxxxxx",
    "category": "all",
    "dry_run": false
  }
  ```

### Export & Import
- **`GET /api/export?format=json|csv&category=all`**: Downloads templates in JSON or CSV format.
- **`POST /api/import`**: Uploads custom templates into memory.
  ```json
  {
    "category": "custom_tests",
    "items": [
      {
        "id_key": "custom_1",
        "title": "Example issue title",
        "body": "Detailed markdown body...",
        "labels": ["bug", "custom"],
        "should_close": false,
        "comments": ["First triage comment"]
      }
    ]
  }
  ```

---

## License
MIT
