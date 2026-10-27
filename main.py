import asyncio
import json
import os
import uuid
import time
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

app = FastAPI(
    title="Secure Cloud Transfer Manager API",
    version="2.4.0",
    description="Enterprise-grade Cloud & Local File Transfer Management System"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- In-Memory State & DB Simulation -----------------

accounts_db = [
    {
        "id": "acc-gdrive-1",
        "provider": "google-drive",
        "name": "Google Drive (Enterprise)",
        "identifier": "corporate-drive@enterprise.org",
        "masked_id": "corp***@enterprise.org",
        "status": "Connected",
        "icon": "gdrive",
        "quota_total_gb": 2048,
        "quota_used_gb": 842,
        "auth_type": "OAuth 2.0 PKCE",
        "token_expires": "2026-11-15T12:00:00Z"
    },
    {
        "id": "acc-onedrive-1",
        "provider": "onedrive",
        "name": "Microsoft OneDrive Business",
        "identifier": "v.kulkarni@techcorp.microsoft.com",
        "masked_id": "v.k***@techcorp.microsoft.com",
        "status": "Connected",
        "icon": "onedrive",
        "quota_total_gb": 1024,
        "quota_used_gb": 310,
        "auth_type": "OAuth 2.0 PKCE",
        "token_expires": "2026-11-20T08:30:00Z"
    },
    {
        "id": "acc-dropbox-1",
        "provider": "dropbox",
        "name": "Dropbox Team Storage",
        "identifier": "storage-team@dropbox-org.com",
        "masked_id": "stor***@dropbox-org.com",
        "status": "Limited Access",
        "icon": "dropbox",
        "quota_total_gb": 5000,
        "quota_used_gb": 4120,
        "auth_type": "OAuth 2.0 PKCE",
        "token_expires": "2026-10-30T10:00:00Z"
    },
    {
        "id": "acc-local-1",
        "provider": "local",
        "name": "Local Filesystem Agent (NVMe Array)",
        "identifier": "WORKSTATION-X99 / D:\\SecureTransfers",
        "masked_id": "WORKSTATION-X99",
        "status": "Connected",
        "icon": "local",
        "quota_total_gb": 4096,
        "quota_used_gb": 1820,
        "auth_type": "mTLS Agent Auth",
        "token_expires": "Never"
    }
]

local_agent_state = {
    "status": "Online",
    "version": "v3.8.2-windows-x64",
    "device_name": "WORKSTATION-X99 (Win 11 Pro Enterprise)",
    "last_seen": datetime.now(timezone.utc).isoformat(),
    "active_transfers": 2,
    "ip_address": "192.168.1.142 (Encrypted WireGuard Tunnel)",
    "storage_path": "D:\\MSEDCL_Vault\\Transfers",
    "heartbeat_interval_s": 5,
    "mtls_fingerprint": "SHA256:8F:B3:99:A1:7C:E2:04:19:B8:22:DF:99:10"
}

transfers_db = [
    {
        "id": "TR-90412",
        "name": "Q3 Financial Vault & Audit Records",
        "source_account_id": "acc-onedrive-1",
        "source_provider": "OneDrive",
        "source_path": "/Finance/2026/Q3_Audit",
        "destination_account_id": "acc-gdrive-1",
        "destination_provider": "Google Drive",
        "destination_path": "/Compliance/Backup_Vault",
        "total_bytes": 128849018880,  # ~120 GB
        "transferred_bytes": 105656195481, # ~98.4 GB
        "total_files": 4520,
        "completed_files": 3706,
        "failed_files": 0,
        "progress_pct": 82.0,
        "speed_mbps": 78.4,
        "status": "Running",
        "started_at": "2026-10-27T18:15:00Z",
        "elapsed_str": "3h 26m",
        "eta_str": "42m remaining",
        "options": {
            "skip_existing": True,
            "verify_integrity": True,
            "preserve_hierarchy": True,
            "concurrency": 8
        }
    },
    {
        "id": "TR-89210",
        "name": "GIS Geospatial Grid Imagery & Substation Data",
        "source_account_id": "acc-local-1",
        "source_provider": "Local Disk",
        "source_path": "D:\\GIS_Surveys\\2026_HighRes",
        "destination_account_id": "acc-gdrive-1",
        "destination_provider": "Google Drive",
        "destination_path": "/Engineering/GIS_Maps",
        "total_bytes": 64424509440, # ~60 GB
        "transferred_bytes": 28991029248, # ~27 GB
        "total_files": 1240,
        "completed_files": 558,
        "failed_files": 2,
        "progress_pct": 45.0,
        "speed_mbps": 42.1,
        "status": "Running",
        "started_at": "2026-10-27T19:40:00Z",
        "elapsed_str": "2h 01m",
        "eta_str": "1h 14m remaining",
        "options": {
            "skip_existing": True,
            "verify_integrity": True,
            "preserve_hierarchy": True,
            "concurrency": 4
        }
    },
    {
        "id": "TR-78201",
        "name": "Customer Billing Database Snapshot 2026-10",
        "source_account_id": "acc-dropbox-1",
        "source_provider": "Dropbox",
        "source_path": "/Databases/Billing_Snapshots/2026-10.tar.gz",
        "destination_account_id": "acc-onedrive-1",
        "destination_provider": "OneDrive",
        "destination_path": "/Backups/Billing",
        "total_bytes": 15032385536, # ~14 GB
        "transferred_bytes": 15032385536,
        "total_files": 1,
        "completed_files": 1,
        "failed_files": 0,
        "progress_pct": 100.0,
        "speed_mbps": 0.0,
        "status": "Completed",
        "started_at": "2026-10-27T14:10:00Z",
        "elapsed_str": "28m 10s",
        "eta_str": "Done",
        "options": {
            "skip_existing": False,
            "verify_integrity": True,
            "preserve_hierarchy": False,
            "concurrency": 2
        }
    },
    {
        "id": "TR-65104",
        "name": "Legacy Meter Log Archives (2023-2025)",
        "source_account_id": "acc-gdrive-1",
        "source_provider": "Google Drive",
        "source_path": "/SmartMeters/RawLogs_Archive",
        "destination_account_id": "acc-local-1",
        "destination_provider": "Local Disk",
        "destination_path": "E:\\ArchiveStorage\\Meters",
        "total_bytes": 42949672960, # ~40 GB
        "transferred_bytes": 18038862643,
        "total_files": 8900,
        "completed_files": 3738,
        "failed_files": 18,
        "progress_pct": 42.0,
        "speed_mbps": 0.0,
        "status": "Paused",
        "started_at": "2026-10-27T11:00:00Z",
        "elapsed_str": "4h 12m",
        "eta_str": "Paused",
        "options": {
            "skip_existing": True,
            "verify_integrity": True,
            "preserve_hierarchy": True,
            "concurrency": 6
        }
    },
    {
        "id": "TR-54019",
        "name": "SCADA Substation Topology Configs",
        "source_account_id": "acc-dropbox-1",
        "source_provider": "Dropbox",
        "source_path": "/SCADA/Configs_v2",
        "destination_account_id": "acc-gdrive-1",
        "destination_provider": "Google Drive",
        "destination_path": "/SCADA_Central/Configs",
        "total_bytes": 2147483648, # ~2 GB
        "transferred_bytes": 536870912,
        "total_files": 150,
        "completed_files": 37,
        "failed_files": 12,
        "progress_pct": 25.0,
        "speed_mbps": 0.0,
        "status": "Failed",
        "started_at": "2026-10-27T09:20:00Z",
        "elapsed_str": "12m",
        "eta_str": "Stopped",
        "options": {
            "skip_existing": False,
            "verify_integrity": True,
            "preserve_hierarchy": True,
            "concurrency": 2
        }
    }
]

recent_activity_db = [
    {
        "id": "act-1",
        "type": "transfer_progress",
        "title": "Transfer Reached 82%",
        "description": "Q3 Financial Vault & Audit Records transferred 98.4 GB of 120 GB",
        "time": "3 mins ago",
        "timestamp": "2026-10-27T21:38:00Z",
        "status": "running",
        "icon": "refresh-cw"
    },
    {
        "id": "act-2",
        "type": "agent_heartbeat",
        "title": "Local Agent Heartbeat Confirmed",
        "description": "Agent WORKSTATION-X99 reported active transfer throughput 42.1 MB/s",
        "time": "5 mins ago",
        "timestamp": "2026-10-27T21:36:00Z",
        "status": "connected",
        "icon": "cpu"
    },
    {
        "id": "act-3",
        "type": "transfer_completed",
        "title": "Transfer Completed & Verified",
        "description": "Customer Billing Database Snapshot 2026-10 SHA-256 integrity match verified",
        "time": "7 hours ago",
        "timestamp": "2026-10-27T14:38:10Z",
        "status": "completed",
        "icon": "check-circle"
    },
    {
        "id": "act-4",
        "type": "account_auth",
        "title": "OAuth Token Refreshed",
        "description": "Google Drive (Enterprise) token renewed with least-privilege OAuth scopes",
        "time": "9 hours ago",
        "timestamp": "2026-10-27T12:00:00Z",
        "status": "connected",
        "icon": "shield-check"
    },
    {
        "id": "act-5",
        "type": "transfer_paused",
        "title": "Transfer Paused by Operator",
        "description": "Legacy Meter Log Archives (2023-2025) paused due to local storage threshold warning",
        "time": "10 hours ago",
        "timestamp": "2026-10-27T11:15:00Z",
        "status": "paused",
        "icon": "pause-circle"
    }
]

audit_logs_db = [
    {
        "id": "AUD-20261027-0941",
        "timestamp": "2026-10-27 21:35:12 UTC",
        "user": "vivek.admin@msedcl.gov.in",
        "role": "Lead Security Engineer",
        "action": "RESUME_TRANSFER",
        "resource": "TR-90412 (Q3 Financial Vault)",
        "outcome": "SUCCESS",
        "request_id": "req-98f21e03a",
        "ip": "192.168.1.142"
    },
    {
        "id": "AUD-20261027-0922",
        "timestamp": "2026-10-27 19:40:02 UTC",
        "user": "vivek.admin@msedcl.gov.in",
        "role": "Lead Security Engineer",
        "action": "CREATE_TRANSFER",
        "resource": "TR-89210 (GIS Geospatial Grid Imagery)",
        "outcome": "SUCCESS",
        "request_id": "req-77bc401f",
        "ip": "192.168.1.142"
    },
    {
        "id": "AUD-20261027-0881",
        "timestamp": "2026-10-27 14:10:00 UTC",
        "user": "system.scheduler",
        "role": "System Automation",
        "action": "START_JOB",
        "resource": "TR-78201 (Customer Billing Snapshot)",
        "outcome": "SUCCESS",
        "request_id": "req-cron-4412",
        "ip": "127.0.0.1"
    },
    {
        "id": "AUD-20261027-0740",
        "timestamp": "2026-10-27 12:00:15 UTC",
        "user": "oauth.service",
        "role": "Auth Service",
        "action": "OAUTH_TOKEN_ROTATE",
        "resource": "acc-gdrive-1 (Enterprise Drive)",
        "outcome": "SUCCESS",
        "request_id": "req-auth-rot-11",
        "ip": "127.0.0.1"
    },
    {
        "id": "AUD-20261027-0630",
        "timestamp": "2026-10-27 09:25:44 UTC",
        "user": "vivek.admin@msedcl.gov.in",
        "role": "Lead Security Engineer",
        "action": "TRANSFER_ERROR_RETRY",
        "resource": "TR-54019 (SCADA Configs)",
        "outcome": "PARTIAL_FAILURE (403 RateLimit)",
        "request_id": "req-retry-9002",
        "ip": "192.168.1.142"
    }
]

# ----------------- Models -----------------

class TransferCreateRequest(BaseModel):
    name: str = Field(..., min_length=3)
    source_account_id: str
    source_path: str
    destination_account_id: str
    destination_path: str
    skip_existing: bool = True
    rename_conflicts: bool = False
    replace_existing: bool = False
    preserve_hierarchy: bool = True
    verify_integrity: bool = True
    concurrency: int = 4
    include_extensions: Optional[str] = ""
    exclude_extensions: Optional[str] = ""

class TransferActionRequest(BaseModel):
    action: str  # pause, resume, cancel, retry

# ----------------- REST Endpoints -----------------

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "app": "Secure Cloud Transfer Manager",
        "version": "2.4.0",
        "server_time": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/user/current")
def get_current_user():
    return {
        "name": "Vivek Kulkarni",
        "email": "vivek.admin@msedcl.gov.in",
        "role": "Enterprise Security Admin",
        "avatar_initials": "VK",
        "mfa_enabled": True,
        "active_session_expires": "2026-10-28T05:00:00Z"
    }

@app.get("/api/dashboard/summary")
def get_dashboard_summary():
    total_bytes = sum(t["total_bytes"] for t in transfers_db)
    completed_bytes = sum(t["transferred_bytes"] for t in transfers_db if t["status"] == "Completed")
    # Add partial progress from running
    transferred_all = sum(t["transferred_bytes"] for t in transfers_db)
    failed_bytes = sum(t["total_bytes"] - t["transferred_bytes"] for t in transfers_db if t["status"] == "Failed")
    
    total_files = sum(t["total_files"] for t in transfers_db)
    completed_files = sum(t["completed_files"] for t in transfers_db)
    failed_files = sum(t["failed_files"] for t in transfers_db)
    
    # Active speed
    active_speed = sum(t["speed_mbps"] for t in transfers_db if t["status"] == "Running")
    
    return {
        "total_data_gb": round(total_bytes / (1024**3), 1),
        "total_data_raw": total_bytes,
        "completed_data_gb": round(transferred_all / (1024**3), 1),
        "completed_files": completed_files,
        "completed_pct": round((transferred_all / total_bytes * 100), 1) if total_bytes > 0 else 0,
        "failed_data_gb": round(failed_bytes / (1024**3), 1),
        "failed_files": failed_files,
        "failed_pct": round((failed_files / total_files * 100), 1) if total_files > 0 else 0,
        "transfer_speed_mbps": round(active_speed, 1),
        "active_jobs_count": len([t for t in transfers_db if t["status"] == "Running"]),
        "total_jobs_count": len(transfers_db)
    }

@app.get("/api/transfers")
def get_transfers(
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = None
):
    results = transfers_db
    if status_filter and status_filter.lower() != "all":
        results = [t for t in results if t["status"].lower() == status_filter.lower()]
    if search:
        s = search.lower()
        results = [
            t for t in results
            if s in t["name"].lower()
            or s in t["source_provider"].lower()
            or s in t["destination_provider"].lower()
            or s in t["id"].lower()
        ]
    return {
        "items": results,
        "total": len(results)
    }

@app.get("/api/transfers/{transfer_id}")
def get_transfer(transfer_id: str):
    for t in transfers_db:
        if t["id"] == transfer_id:
            return t
    raise HTTPException(status_code=404, detail="Transfer job not found")

@app.post("/api/transfers")
def create_transfer(payload: TransferCreateRequest):
    # Lookup source & dest
    src_acc = next((a for a in accounts_db if a["id"] == payload.source_account_id), None)
    dest_acc = next((a for a in accounts_db if a["id"] == payload.destination_account_id), None)
    
    if not src_acc or not dest_acc:
        raise HTTPException(status_code=400, detail="Invalid source or destination account")
    
    # Generate job
    new_id = f"TR-{int(time.time()) % 100000}"
    # Simulated realistic file scan estimate
    sim_size = 25 * 1024 * 1024 * 1024 # 25 GB
    new_job = {
        "id": new_id,
        "name": payload.name,
        "source_account_id": src_acc["id"],
        "source_provider": src_acc["name"].split(" ")[0],
        "source_path": payload.source_path,
        "destination_account_id": dest_acc["id"],
        "destination_provider": dest_acc["name"].split(" ")[0],
        "destination_path": payload.destination_path,
        "total_bytes": sim_size,
        "transferred_bytes": 0,
        "total_files": 1420,
        "completed_files": 0,
        "failed_files": 0,
        "progress_pct": 0.0,
        "speed_mbps": 45.0,
        "status": "Running",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "elapsed_str": "Just now",
        "eta_str": "Calculating...",
        "options": payload.model_dump()
    }
    transfers_db.insert(0, new_job)
    
    # Record Audit
    audit_logs_db.insert(0, {
        "id": f"AUD-{datetime.now().strftime('%Y%m%d')}-{int(time.time())%10000}",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "user": "vivek.admin@msedcl.gov.in",
        "role": "Enterprise Security Admin",
        "action": "CREATE_TRANSFER",
        "resource": f"{new_id} ({payload.name})",
        "outcome": "SUCCESS",
        "request_id": f"req-{uuid.uuid4().hex[:8]}",
        "ip": "192.168.1.142"
    })
    
    recent_activity_db.insert(0, {
        "id": f"act-{uuid.uuid4().hex[:6]}",
        "type": "transfer_started",
        "title": f"Transfer Initialized: {payload.name}",
        "description": f"Transferring from {src_acc['name']} to {dest_acc['name']}",
        "time": "Just now",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "running",
        "icon": "play"
    })
    
    return {"status": "success", "job": new_job}

@app.post("/api/transfers/{transfer_id}/action")
def update_transfer_action(transfer_id: str, body: TransferActionRequest):
    t = next((item for item in transfers_db if item["id"] == transfer_id), None)
    if not t:
        raise HTTPException(status_code=404, detail="Transfer not found")
        
    act = body.action.lower()
    if act == "pause":
        t["status"] = "Paused"
        t["speed_mbps"] = 0.0
    elif act == "resume":
        t["status"] = "Running"
        t["speed_mbps"] = 54.2
    elif act == "cancel":
        t["status"] = "Cancelled"
        t["speed_mbps"] = 0.0
    elif act == "retry":
        t["status"] = "Running"
        t["speed_mbps"] = 48.0
        t["failed_files"] = 0
    else:
        raise HTTPException(status_code=400, detail="Invalid action")
        
    audit_logs_db.insert(0, {
        "id": f"AUD-{datetime.now().strftime('%Y%m%d')}-{int(time.time())%10000}",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "user": "vivek.admin@msedcl.gov.in",
        "role": "Enterprise Security Admin",
        "action": f"{act.upper()}_TRANSFER",
        "resource": f"{t['id']} ({t['name']})",
        "outcome": "SUCCESS",
        "request_id": f"req-{uuid.uuid4().hex[:8]}",
        "ip": "192.168.1.142"
    })
    
    return {"status": "success", "transfer": t}

@app.get("/api/accounts")
def get_accounts():
    return {"items": accounts_db, "total": len(accounts_db)}

@app.post("/api/accounts/{account_id}/reconnect")
def reconnect_account(account_id: str):
    acc = next((a for a in accounts_db if a["id"] == account_id), None)
    if not acc:
        raise HTTPException(status_code=404, detail="Account not found")
    acc["status"] = "Connected"
    return {"status": "success", "message": f"{acc['name']} successfully re-authenticated via OAuth 2.0 PKCE."}

@app.get("/api/agent")
def get_agent_status():
    local_agent_state["last_seen"] = datetime.now(timezone.utc).isoformat()
    return local_agent_state

@app.get("/api/activity")
def get_activity():
    return {"items": recent_activity_db[:8]}

@app.get("/api/audit-logs")
def get_audit_logs(search: Optional[str] = None):
    results = audit_logs_db
    if search:
        s = search.lower()
        results = [r for r in results if s in r["action"].lower() or s in r["resource"].lower() or s in r["user"].lower()]
    return {"items": results, "total": len(results)}

# ----------------- WebSocket Live Real-Time Feed -----------------

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

@app.websocket("/ws/transfers")
async def websocket_transfers_feed(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Send periodic pulse of active jobs progress
            await asyncio.sleep(2)
            # Update progress on running jobs realistically
            for t in transfers_db:
                if t["status"] == "Running":
                    # add small incremental bytes
                    inc = int(t["speed_mbps"] * 1024 * 1024 * 2) # 2 seconds of transfer
                    t["transferred_bytes"] = min(t["total_bytes"], t["transferred_bytes"] + inc)
                    t["progress_pct"] = round((t["transferred_bytes"] / t["total_bytes"]) * 100, 1)
                    if t["progress_pct"] >= 100:
                        t["status"] = "Completed"
                        t["speed_mbps"] = 0.0
                        t["eta_str"] = "Done"
            
            summary = get_dashboard_summary()
            await websocket.send_json({
                "type": "PROGRESS_PULSE",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "transfers": transfers_db,
                "summary": summary
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)

# ----------------- Mount Frontend Static Files -----------------

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/{full_path:path}")
def serve_spa(full_path: str):
    if full_path.startswith("api/") or full_path.startswith("ws/"):
        raise HTTPException(status_code=404, detail="API endpoint not found")
    index_file = os.path.join(static_dir, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return JSONResponse({"status": "API Server Ready", "docs": "/docs"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
