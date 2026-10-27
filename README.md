# Secure Cloud Transfer Manager — Enterprise UI & Service Architecture

A professional, modern, secure, and responsive web dashboard designed for large-volume file migrations across multi-cloud storage ecosystems (Google Drive, Microsoft OneDrive, Dropbox) and on-premises local workstations.

---

## 🚀 Key Highlights & Architectural Features

### 1. Executive Dashboard & Metrics
- **Dark Navy Sidebar (`#0B1528`)**: Professional navigation structure featuring Dashboard, Transfers, Accounts, Local Agent, Audit Logs, and Settings. Includes security compliance badge (*TLS 1.3 / AES-256 / Zero-Knowledge*).
- **Summary Cards (API-Driven)**:
  - **Total Data**: Real-time aggregated bytes selected for transfer.
  - **Completed**: Verified payload volume, total file counts, and cryptographic SHA-256 integrity validation rate.
  - **Failed**: Error logs with automatic retry queue status.
  - **Transfer Speed**: Dynamic throughput in MB/s with live WebSocket updates.

### 2. Multi-Step Transfer Pipeline Wizard
- **Step 1: Select Source**: Choose connected cloud accounts or local NVMe storage and designate source path.
- **Step 2: Select Destination**: Select target provider and remote folder.
- **Step 3: Transfer Options**: Safe conflict handling (Skip existing, Hash comparison, Preserve subfolder directory hierarchy, Concurrency stream throttle).
- **Step 4: Dry-Run Preview & Confirmation**: Explicit confirmation, persistent job creation, and dry-run conflict detection.

### 3. Connected Accounts & Local Windows Agent
- **Cloud OAuth 2.0 PKCE**: Token lifecycle tracking, least-privilege scopes, and seamless one-click re-authorization.
- **Local Workstation Agent**: On-premises Windows service status monitoring, heartbeat diagnostics, and mTLS cryptographic fingerprint verification.

### 4. Live Updates & Real-Time Telemetry
- **WebSocket Feed (`/ws/transfers`)**: Real-time pulse streaming progress percentages, transferred bytes, and throughput changes without browser polling.
- **Full Audit Trail (`/api/audit-logs`)**: Chronological audit logging recording operator, timestamp, request trace ID, and operation outcome.

---

## 🛠️ Technology Stack
- **Frontend**: React 18, Tailwind CSS, Lucide Icons, WebSocket client.
- **Backend**: FastAPI (Python 3.15), Uvicorn ASGI server, Pydantic v2 schemas.
- **Transport**: RESTful JSON endpoints + WebSocket bidirectional feeds.

---

## 🏃 Running the Application

### 1. Start Backend & Static Server
```bash
py main.py
```
*The server will start on `http://127.0.0.1:8000`.*

### 2. Access the Application
Open your web browser and navigate to:
**`http://127.0.0.1:8000/`**
