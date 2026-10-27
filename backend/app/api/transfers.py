import time
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.orm import Session
from backend.app.database import get_db
from backend.app.models import User, TransferJob, ConnectedAccount
from backend.app.schemas import TransferCreateRequest, TransferActionRequest, TransferResponse
from backend.app.security.dependencies import get_current_user, require_write_user
from backend.app.services.audit_service import log_audit_event

router = APIRouter(prefix="/transfers", tags=["Transfers"])

@router.get("", response_model=List[TransferResponse])
def list_transfers(
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(TransferJob)
    # Role-based filtering
    if current_user.role != "admin":
        query = query.filter(TransferJob.user_id == current_user.id)

    if status_filter and status_filter.lower() != "all":
        query = query.filter(TransferJob.status == status_filter)

    jobs = query.order_by(TransferJob.started_at.desc()).all()
    
    if search:
        s = search.lower()
        jobs = [j for j in jobs if s in j.name.lower() or s in j.id.lower() or s in j.source_provider.lower()]

    results = []
    for j in jobs:
        results.append(
            TransferResponse(
                id=j.id,
                name=j.name,
                source_account_id=j.source_account_id,
                source_provider=j.source_provider,
                source_path=j.source_path,
                destination_account_id=j.destination_account_id,
                destination_provider=j.destination_provider,
                destination_path=j.destination_path,
                total_bytes=j.total_bytes,
                transferred_bytes=j.transferred_bytes,
                total_files=j.total_files,
                completed_files=j.completed_files,
                failed_files=j.failed_files,
                progress_pct=j.progress_pct,
                speed_mbps=j.speed_mbps,
                status=j.status,
                started_at=j.started_at,
                elapsed_str="2h 15m"
            )
        )
    return results

@router.post("", status_code=status.HTTP_201_CREATED)
def create_transfer_job(
    payload: TransferCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_write_user)
):
    # Idempotency check to prevent duplicate transfers
    if payload.idempotency_key:
        existing = db.query(TransferJob).filter(TransferJob.idempotency_key == payload.idempotency_key).first()
        if existing:
            return {"status": "success", "message": "Job already exists (idempotent)", "job": existing}

    # Verify source and destination exist
    src = db.query(ConnectedAccount).filter(ConnectedAccount.id == payload.source_account_id).first()
    dst = db.query(ConnectedAccount).filter(ConnectedAccount.id == payload.destination_account_id).first()
    if not src or not dst:
        raise HTTPException(status_code=400, detail="Invalid source or destination account")

    job_id = f"TR-{int(time.time()) % 100000}"
    simulated_bytes = 45 * 1024 * 1024 * 1024  # 45 GB

    job = TransferJob(
        id=job_id,
        user_id=current_user.id,
        name=payload.name,
        source_account_id=src.id,
        source_provider=src.name.split(" ")[0],
        source_path=payload.source_path,
        destination_account_id=dst.id,
        destination_provider=dst.name.split(" ")[0],
        destination_path=payload.destination_path,
        total_bytes=simulated_bytes,
        transferred_bytes=0,
        total_files=820,
        completed_files=0,
        failed_files=0,
        progress_pct=0.0,
        speed_mbps=52.4,
        status="Running",
        idempotency_key=payload.idempotency_key,
        options={
            "skip_existing": payload.skip_existing,
            "verify_integrity": payload.verify_integrity,
            "preserve_hierarchy": payload.preserve_hierarchy,
            "concurrency": payload.concurrency
        }
    )
    db.add(job)
    db.commit()

    log_audit_event(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=current_user.role,
        action="CREATE_TRANSFER",
        resource=f"{job_id} ({payload.name})",
        outcome="SUCCESS",
        ip_address=request.client.host if request.client else "127.0.0.1"
    )

    return {"status": "success", "job": {"id": job.id, "name": job.name, "status": job.status}}

@router.post("/{transfer_id}/pause")
def pause_transfer(
    transfer_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_write_user)
):
    job = db.query(TransferJob).filter(TransferJob.id == transfer_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Transfer not found")
    if current_user.role != "admin" and job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this transfer")

    job.status = "Paused"
    job.speed_mbps = 0.0
    db.commit()

    log_audit_event(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=current_user.role,
        action="PAUSE_TRANSFER",
        resource=f"{job.id} ({job.name})",
        outcome="SUCCESS",
        ip_address=request.client.host if request.client else "127.0.0.1"
    )
    return {"status": "success", "transfer": {"id": job.id, "status": job.status}}

@router.post("/{transfer_id}/resume")
def resume_transfer(
    transfer_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_write_user)
):
    job = db.query(TransferJob).filter(TransferJob.id == transfer_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Transfer not found")
    if current_user.role != "admin" and job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this transfer")

    job.status = "Running"
    job.speed_mbps = 48.5
    db.commit()

    log_audit_event(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=current_user.role,
        action="RESUME_TRANSFER",
        resource=f"{job.id} ({job.name})",
        outcome="SUCCESS",
        ip_address=request.client.host if request.client else "127.0.0.1"
    )
    return {"status": "success", "transfer": {"id": job.id, "status": job.status}}

@router.post("/{transfer_id}/cancel")
def cancel_transfer(
    transfer_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_write_user)
):
    job = db.query(TransferJob).filter(TransferJob.id == transfer_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Transfer not found")
    if current_user.role != "admin" and job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this transfer")

    job.status = "Cancelled"
    job.speed_mbps = 0.0
    db.commit()

    log_audit_event(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=current_user.role,
        action="CANCEL_TRANSFER",
        resource=f"{job.id} ({job.name})",
        outcome="SUCCESS",
        ip_address=request.client.host if request.client else "127.0.0.1"
    )
    return {"status": "success", "transfer": {"id": job.id, "status": job.status}}

@router.post("/{transfer_id}/retry")
def retry_transfer(
    transfer_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_write_user)
):
    job = db.query(TransferJob).filter(TransferJob.id == transfer_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Transfer not found")
    if current_user.role != "admin" and job.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this transfer")

    job.status = "Running"
    job.speed_mbps = 55.0
    job.failed_files = 0
    db.commit()

    log_audit_event(
        db=db,
        user_id=current_user.id,
        user_email=current_user.email,
        user_role=current_user.role,
        action="RETRY_TRANSFER",
        resource=f"{job.id} ({job.name})",
        outcome="SUCCESS",
        ip_address=request.client.host if request.client else "127.0.0.1"
    )
    return {"status": "success", "transfer": {"id": job.id, "status": job.status}}
