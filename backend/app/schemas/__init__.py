from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# --- Auth Schemas ---
class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str
    role: Optional[str] = "user"

class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    is_active: bool
    avatar_initials: Optional[str] = None

    class Config:
        from_attributes = True

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse

# --- Connected Account Schemas ---
class AccountResponse(BaseModel):
    id: str
    provider: str
    name: str
    identifier: str
    masked_id: str
    status: str
    auth_type: str
    quota_total_gb: float
    quota_used_gb: float
    token_expires: Optional[str] = None

    class Config:
        from_attributes = True

class AccountConnectRequest(BaseModel):
    provider: str
    account_name: Optional[str] = None

# --- Registered Agent Schemas ---
class AgentEnrollRequest(BaseModel):
    device_name: str
    version: Optional[str] = "v3.8.2-windows-x64"
    storage_path: Optional[str] = "C:\\Transfers"

class AgentHeartbeatRequest(BaseModel):
    agent_id: str
    active_transfers: int = 0
    throughput_mbps: float = 0.0

class AgentResponse(BaseModel):
    id: str
    device_name: str
    status: str
    version: str
    last_seen: datetime
    active_transfers: int
    ip_address: str
    storage_path: str
    mtls_fingerprint: Optional[str] = None

    class Config:
        from_attributes = True

# --- Transfer Schemas ---
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
    idempotency_key: Optional[str] = None

class TransferActionRequest(BaseModel):
    action: str  # pause, resume, cancel, retry

class TransferResponse(BaseModel):
    id: str
    name: str
    source_account_id: str
    source_provider: str
    source_path: str
    destination_account_id: str
    destination_provider: str
    destination_path: str
    total_bytes: int
    transferred_bytes: int
    total_files: int
    completed_files: int
    failed_files: int
    progress_pct: float
    speed_mbps: float
    status: str
    started_at: datetime
    elapsed_str: Optional[str] = "Just now"

    class Config:
        from_attributes = True

# --- Audit Schemas ---
class AuditLogResponse(BaseModel):
    id: str
    timestamp: datetime
    user: str
    role: str
    action: str
    resource: str
    outcome: str
    request_id: str
    ip: str

    class Config:
        from_attributes = True
