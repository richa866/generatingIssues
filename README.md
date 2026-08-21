# RepoGuardian Test Suite Controller & Issue Generator

A FastAPI-powered web application and REST engine designed to generate realistic GitHub issue scenarios, labels, cross-referencing comments, and lifecycle states directly into target GitHub repositories for tool testing, AI evaluation, and demonstration purposes.

---

## 🚀 Features

- **Automated Issue Generation**: Seed realistic issue suites directly into any GitHub repository using the GitHub REST API.
- **Categorized Test Scenarios**:
  - 👯 **Duplicates**: Generates multiple similar issues (e.g. auth expiration loops, YAML parsing bugs) with cross-references.
  - 🔁 **Regressions**: Seeds previously closed issues followed by open regressions to test version tracking.
  - 🔒 **Security**: Simulates vulnerability reports such as path traversal, SQL injection, and credential leaks.
  - 🔥 **Contentious**: Simulates heated multi-comment discussions (e.g. breaking changes, ESM migration).
  - ✅ **Controls**: Baseline feature requests and documentation fixes with merge comments.
  - 🚀 **Seed All**: Injects the entire test suite in sequential passes.
- **Interactive Web Interface**: Clean web UI to configure credentials, trigger seeding, and view live real-time execution logs.
- **Dynamic Cross-Referencing**: Automatically resolves issue numbers dynamically in multi-pass comments (e.g., referencing `#<issue_id>`).

---

## 🛠️ Prerequisites

- **Python**: Version 3.8 or higher
- **GitHub Personal Access Token (PAT)**: Requires `repo` scope to create and manage issues and comments.

---

## 📦 Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/darshnagraniwork-png/generatingIssues.git
   cd generatingIssues
   ```

2. **Create and activate a virtual environment**:
   - **Linux / macOS**:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```
   - **Windows (PowerShell)**:
     ```powershell
     python -m venv venv
     .\venv\Scripts\Activate.ps1
     ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

---

## 💻 Usage

1. **Start the application**:
   ```bash
   python app.py
   ```
   *Alternatively, using uvicorn directly:*
   ```bash
   uvicorn app:app --reload --host 127.0.0.1 --port 8000
   ```

2. **Open the Web UI**:
   Navigate to [http://127.0.0.1:8000](http://127.0.0.1:8000) in your web browser.

3. **Configure & Run**:
   - Enter the **GitHub Owner / Org** (e.g. `your-username`).
   - Enter the **Repository Name** (e.g. `test-repo`).
   - Enter your **Personal Access Token** (PAT).
   - Click any category button or **Seed All Data** to execute.

---

## 📡 API Reference

### Seed Endpoint
- **URL**: `/api/seed`
- **Method**: `POST`
- **Request Body**:
  ```json
  {
    "owner": "github-username-or-org",
    "repo": "repository-name",
    "token": "ghp_yourPersonalAccessToken",
    "category": "all" 
  }
  ```
  *Allowed categories*: `all`, `duplicates`, `regressions`, `security`, `contentious`, `controls`

- **Sample Response**:
  ```json
  {
    "status": "success",
    "logs": [
      "Created Issue #1: Background worker hits 401 Unauthorized...",
      "Created Issue #2: CLI daemon gets stuck in auth failure loop...",
      "  └ Added comment to #2",
      "  └ Closed Issue #5"
    ]
  }
  ```

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).
