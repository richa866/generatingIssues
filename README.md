# RepoGuardian Issue Seeding Controller

A FastAPI-powered automation dashboard and REST API designed to generate realistic GitHub issues, cross-references, regression scenarios, security alerts, and contentious threads into live repositories for benchmarking and triage testing.

---

## ✨ Features

- 🚀 **Full Suite Seeding**: Inject realistic issues across multiple categories (Duplicates, Regressions, Security CVEs, Contentious discussions, Controls).
- 🧪 **Dry Run Simulation Mode**: Test and validate issue structures, labels, and dynamic comment references without hitting the GitHub API.
- 🩺 **Health & Stats API**: Inspect available templates and category breakdowns via `/api/health` and `/api/categories`.
- 💻 **Modern Dark-Mode UI**: Built-in Tailwind dashboard for manual execution and live streaming logs.

---

## 🛠️ Getting Started

### 1. Installation

Install required dependencies:

```bash
pip install -r requirements.txt
```

### 2. Running the Server

Start the FastAPI application with Uvicorn:

```bash
python app.py
```

Or with `uvicorn`:

```bash
uvicorn app:app --reload --port 8000
```

Access the dashboard at `http://127.0.0.1:8000`.

---

## 📡 API Reference

### Health Check
```http
GET /api/health
```
**Response:**
```json
{
  "status": "healthy",
  "service": "RepoGuardian Test Suite Controller",
  "version": "1.1.0",
  "categories": ["duplicates", "regressions", "security", "contentious", "controls"],
  "total_seed_templates": 14
}
```

### Category Metadata
```http
GET /api/categories
```

### Trigger Seeding
```http
POST /api/seed
Content-Type: application/json

{
  "owner": "your-org",
  "repo": "your-repo",
  "token": "ghp_xxxxxxxxxxxx",
  "category": "duplicates",
  "dry_run": true
}
```
