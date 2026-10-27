# Windows Local Agent Installation & Setup Guide

The Secure Cloud Transfer Manager local agent connects on-premises disks, NVMe arrays, and workstations to cloud pipelines.

---

## 1. Enrollment
1. An administrator creates an agent enrollment token via the web dashboard under **Local Agent** or via API:
   ```http
   POST /api/v1/agents/enroll
   Content-Type: application/json

   {
     "device_name": "WORKSTATION-X99",
     "storage_path": "D:\\SecureTransfers"
   }
   ```
2. The server generates a unique `agent_id` and raw secret token. The raw token is hashed and never displayed again.

---

## 2. Agent Configuration
The agent stores its configuration in `agent/agent_config.json`:
```json
{
  "agent_id": "agent-x99-enterprise",
  "device_name": "WORKSTATION-X99",
  "agent_token": "your_enrollment_token",
  "storage_root": "D:\\SecureTransfers",
  "heartbeat_interval_sec": 10
}
```

---

## 3. Running the Agent Service
Run the service directly using Python on Windows:
```powershell
cd "agent"
py windows_agent.py
```

### Features:
- **Local SQLite Checkpoints**: File transfer progress and SHA-256 byte offsets are committed to `agent_checkpoints.db`. If power is lost or the network drops, transfers resume without restarting.
- **TLS Authenticated Heartbeats**: Pings backend with active throughput every 10 seconds.
- **Revocation**: If revoked in the dashboard, the backend rejects future heartbeats immediately with HTTP 403.
