import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, BigInteger, Float, Boolean, DateTime, ForeignKey, Text, JSON
)
from sqlalchemy.orm import relationship
from backend.app.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="user", nullable=False)  # admin, user, read_only
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    accounts = relationship("ConnectedAccount", back_populates="user", cascade="all, delete-orphan")
    transfers = relationship("TransferJob", back_populates="user", cascade="all, delete-orphan")
    agents = relationship("RegisteredAgent", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user")


class ConnectedAccount(Base):
    __tablename__ = "connected_accounts"

    id = Column(String(50), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    provider = Column(String(50), nullable=False)  # google-drive, onedrive, dropbox, local
    name = Column(String(255), nullable=False)
    identifier = Column(String(255), nullable=False)
    masked_id = Column(String(100), nullable=False)
    status = Column(String(50), default="Connected", nullable=False)  # Connected, Limited Access, Expired, Revoked, Disconnected
    auth_type = Column(String(50), default="OAuth 2.0 PKCE", nullable=False)
    encrypted_access_token = Column(Text, nullable=True)
    encrypted_refresh_token = Column(Text, nullable=True)
    token_expires_at = Column(DateTime, nullable=True)
    quota_total_gb = Column(Float, default=100.0)
    quota_used_gb = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="accounts")


class RegisteredAgent(Base):
    __tablename__ = "registered_agents"

    id = Column(String(50), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    device_name = Column(String(255), nullable=False)
    status = Column(String(50), default="Online", nullable=False)  # Online, Offline, Revoked
    version = Column(String(50), default="v3.8.2-windows-x64", nullable=False)
    last_seen = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    active_transfers = Column(Integer, default=0)
    ip_address = Column(String(100), default="127.0.0.1")
    storage_path = Column(String(500), default="C:\\Transfers")
    mtls_fingerprint = Column(String(255), nullable=True)
    api_token_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="agents")


class TransferJob(Base):
    __tablename__ = "transfer_jobs"

    id = Column(String(50), primary_key=True)  # e.g., TR-90412
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    source_account_id = Column(String(50), nullable=False)
    source_provider = Column(String(50), nullable=False)
    source_path = Column(String(1000), nullable=False)
    destination_account_id = Column(String(50), nullable=False)
    destination_provider = Column(String(50), nullable=False)
    destination_path = Column(String(1000), nullable=False)
    
    total_bytes = Column(BigInteger, default=0)
    transferred_bytes = Column(BigInteger, default=0)
    total_files = Column(Integer, default=0)
    completed_files = Column(Integer, default=0)
    failed_files = Column(Integer, default=0)
    progress_pct = Column(Float, default=0.0)
    speed_mbps = Column(Float, default=0.0)
    status = Column(String(50), default="Pending", nullable=False)  # Pending, Running, Paused, Completed, Failed, Cancelled
    
    idempotency_key = Column(String(100), unique=True, nullable=True, index=True)
    options = Column(JSON, default=dict)
    
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="transfers")
    manifest_items = relationship("TransferManifestItem", back_populates="transfer", cascade="all, delete-orphan")


class TransferManifestItem(Base):
    __tablename__ = "transfer_manifest_items"

    id = Column(String(50), primary_key=True, default=generate_uuid)
    transfer_id = Column(String(50), ForeignKey("transfer_jobs.id"), nullable=False, index=True)
    relative_path = Column(String(1000), nullable=False)
    file_size = Column(BigInteger, default=0)
    source_hash_sha256 = Column(String(64), nullable=True)
    destination_hash_sha256 = Column(String(64), nullable=True)
    bytes_transferred = Column(BigInteger, default=0)
    status = Column(String(50), default="Pending")  # Pending, Transferring, Completed, Failed, Verified
    error_message = Column(Text, nullable=True)
    resumable_session_url = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    transfer = relationship("TransferJob", back_populates="manifest_items")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(50), primary_key=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    user_email = Column(String(255), nullable=False)
    user_role = Column(String(50), nullable=False)
    action = Column(String(100), nullable=False)
    resource = Column(String(255), nullable=False)
    outcome = Column(String(100), nullable=False)
    request_id = Column(String(100), nullable=False)
    ip_address = Column(String(50), default="127.0.0.1")

    user = relationship("User", back_populates="audit_logs")
