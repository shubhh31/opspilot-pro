from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Task, AuditLog
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timedelta
import random

router = APIRouter(prefix="/api/tasks", tags=["Tasks"])

# Pydantic Schemas for Input Validation
class TaskCreate(BaseModel):
    sap_id: Optional[str] = None
    title: str
    description: Optional[str] = None
    department: str
    status: Optional[str] = "Pending"
    priority: Optional[str] = "Medium"
    due_date: str
    assigned_to: str
    amount: Optional[float] = 0.0

class TaskUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[str] = None
    delayed: Optional[bool] = None
    delay_reason: Optional[str] = None

class TaskResponse(BaseModel):
    id: int
    sap_id: Optional[str]
    title: str
    description: Optional[str]
    department: str
    status: str
    priority: str
    due_date: str
    assigned_to: str
    created_at: datetime
    delayed: bool
    delay_reason: Optional[str]
    amount: float

    class Config:
        from_attributes = True

class AuditLogResponse(BaseModel):
    id: int
    task_id: Optional[int]
    action: str
    performed_by: str
    timestamp: datetime
    details: Optional[str]

    class Config:
        from_attributes = True

# GET all tasks
@router.get("/", response_model=List[TaskResponse])
def get_tasks(db: Session = Depends(get_db)):
    return db.query(Task).order_by(Task.created_at.desc()).all()

# GET task analytics summary
@router.get("/analytics")
def get_analytics(db: Session = Depends(get_db)):
    tasks = db.query(Task).all()
    
    total = len(tasks)
    if total == 0:
        return {
            "total_tasks": 0,
            "pending_count": 0,
            "delayed_count": 0,
            "approved_count": 0,
            "rejected_count": 0,
            "total_value": 0.0,
            "delayed_value": 0.0,
            "department_stats": {},
            "priority_stats": {},
            "bottlenecks": []
        }

    pending = len([t for t in tasks if t.status == "Pending"])
    delayed = len([t for t in tasks if t.delayed or t.status == "Delayed"])
    approved = len([t for t in tasks if t.status == "Approved"])
    rejected = len([t for t in tasks if t.status == "Rejected"])
    in_progress = len([t for t in tasks if t.status == "In Progress"])
    
    total_value = sum(t.amount for t in tasks)
    delayed_value = sum(t.amount for t in tasks if t.delayed or t.status == "Delayed")

    # Group by department
    dept_stats = {}
    for t in tasks:
        dept = t.department
        if dept not in dept_stats:
            dept_stats[dept] = {"total": 0, "pending": 0, "delayed": 0, "value": 0.0}
        dept_stats[dept]["total"] += 1
        if t.status == "Pending":
            dept_stats[dept]["pending"] += 1
        if t.delayed or t.status == "Delayed":
            dept_stats[dept]["delayed"] += 1
        dept_stats[dept]["value"] += t.amount

    # Group by priority
    priority_stats = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
    for t in tasks:
        p = t.priority
        if p in priority_stats:
            priority_stats[p] += 1

    # Find department bottlenecks (most delayed or pending)
    bottlenecks = []
    for dept, stats in dept_stats.items():
        if stats["delayed"] > 0 or stats["pending"] > 1:
            ratio = (stats["delayed"] + stats["pending"]) / stats["total"]
            bottlenecks.append({
                "department": dept,
                "delayed_count": stats["delayed"],
                "pending_count": stats["pending"],
                "total_count": stats["total"],
                "risk_factor": round(ratio * 10, 1) # out of 10
            })
    bottlenecks = sorted(bottlenecks, key=lambda x: x["risk_factor"], reverse=True)

    return {
        "total_tasks": total,
        "pending_count": pending,
        "delayed_count": delayed,
        "approved_count": approved,
        "rejected_count": rejected,
        "in_progress_count": in_progress,
        "total_value": round(total_value, 2),
        "delayed_value": round(delayed_value, 2),
        "department_stats": dept_stats,
        "priority_stats": priority_stats,
        "bottlenecks": bottlenecks[:3] # top 3 bottlenecks
    }

# POST Create new manual task
@router.post("/", response_model=TaskResponse)
def create_task(task_data: TaskCreate, db: Session = Depends(get_db)):
    # Generate SAP ID if not provided
    sap_id = task_data.sap_id
    if not sap_id:
        sap_id = f"PO-{random.randint(4500000000, 4500999999)}"

    # Check if due date is valid, default to 7 days from now if error
    try:
        datetime.strptime(task_data.due_date, "%Y-%m-%d")
    except ValueError:
        task_data.due_date = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

    db_task = Task(
        sap_id=sap_id,
        title=task_data.title,
        description=task_data.description,
        department=task_data.department,
        status=task_data.status,
        priority=task_data.priority,
        due_date=task_data.due_date,
        assigned_to=task_data.assigned_to,
        amount=task_data.amount
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)

    # Create audit log
    audit = AuditLog(
        task_id=db_task.id,
        action="Created",
        performed_by="Manager (System)",
        details=f"Task initiated for {db_task.department}. SAP ID: {db_task.sap_id}. Value: ₹{db_task.amount:,.2f}"
    )
    db.add(audit)
    db.commit()
    
    return db_task

# PUT Update task (e.g. approve/reject or mark delayed)
@router.put("/{task_id}", response_model=TaskResponse)
def update_task(task_id: int, task_data: TaskUpdate, db: Session = Depends(get_db)):
    db_task = db.query(Task).filter(Task.id == task_id).first()
    if not db_task:
        raise HTTPException(status_code=404, detail="Task not found")

    original_status = db_task.status
    
    # Update fields
    if task_data.status is not None:
        db_task.status = task_data.status
    if task_data.priority is not None:
        db_task.priority = task_data.priority
    if task_data.assigned_to is not None:
        db_task.assigned_to = task_data.assigned_to
    if task_data.delayed is not None:
        db_task.delayed = task_data.delayed
        if task_data.delayed:
            db_task.status = "Delayed"
    if task_data.delay_reason is not None:
        db_task.delay_reason = task_data.delay_reason

    db.commit()
    db.refresh(db_task)

    # Log specific audit events
    action = "Updated"
    details = f"Task parameters modified."
    
    if task_data.status and task_data.status != original_status:
        action = task_data.status
        details = f"Status changed from '{original_status}' to '{task_data.status}'."
        if task_data.status == "Approved":
            details += " Fund release authorization issued."
        elif task_data.status == "Rejected":
            details += " Workflow terminated and returned to sender."
    
    if task_data.delayed:
        action = "Delayed Warning"
        details = f"Task flagged as delayed. Reason: {task_data.delay_reason or 'Not provided'}."

    audit = AuditLog(
        task_id=db_task.id,
        action=action,
        performed_by="Manager (System)",
        details=details
    )
    db.add(audit)
    db.commit()

    return db_task

# GET audit trail for a task
@router.get("/{task_id}/audit", response_model=List[AuditLogResponse])
def get_task_audit(task_id: int, db: Session = Depends(get_db)):
    logs = db.query(AuditLog).filter(AuditLog.task_id == task_id).order_by(AuditLog.timestamp.desc()).all()
    return logs

# POST Seed tasks database
@router.post("/seed")
def seed_database(db: Session = Depends(get_db)):
    # Clear existing
    db.query(AuditLog).delete()
    db.query(Task).delete()
    db.commit()

    # Pre-defined high fidelity mock tasks representing classic corporate SAP blockages
    mock_tasks = [
        {
            "sap_id": "PO-4500109281",
            "title": "Raw Materials Procurement",
            "description": "Bulk steel coil shipment approval for automotive structural frames.",
            "department": "Procurement",
            "status": "Delayed",
            "priority": "Critical",
            "due_date": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"),
            "assigned_to": "Sarah Jenkins (Head of Purchasing)",
            "delayed": True,
            "delay_reason": "Vendor credit limit holds triggered. Awaiting legal review of updated surety bond.",
            "amount": 284500.00
        },
        {
            "sap_id": "PO-4500109315",
            "title": "Data Center UPS Upgrade",
            "description": "Purchase order approval for double-redundant battery modules in Munich main hub.",
            "department": "Finance",
            "status": "Pending",
            "priority": "High",
            "due_date": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d"),
            "assigned_to": "Robert Vance (Finance VP)",
            "delayed": False,
            "delay_reason": None,
            "amount": 142000.00
        },
        {
            "sap_id": "PO-4500109401",
            "title": "Industrial Boiler Lease Renewal",
            "description": "Quarterly payment for Plant 4 steam boilers.",
            "department": "Finance",
            "status": "Delayed",
            "priority": "High",
            "due_date": (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"),
            "assigned_to": "David Patel (Controller)",
            "delayed": True,
            "delay_reason": "Mismatched invoice quantities vs goods receipt (GR/IR variance exceeds 5%). Awaiting audit verification.",
            "amount": 89300.00
        },
        {
            "sap_id": "PO-4500109450",
            "title": "Vendor NDA and Compliance Audit",
            "description": "Compliance check for logistics partner operating in Eastern Europe routes.",
            "department": "Legal",
            "status": "Pending",
            "priority": "Medium",
            "due_date": (datetime.now() + timedelta(days=12)).strftime("%Y-%m-%d"),
            "assigned_to": "Elena Rostova (Compliance Counsel)",
            "delayed": False,
            "delay_reason": None,
            "amount": 12500.00
        },
        {
            "sap_id": "PO-4500109489",
            "title": "Warehouse Sorting System Spares",
            "description": "Emergency pneumatic cylinder parts order for terminal sorting conveyor belt.",
            "department": "Warehouse",
            "status": "Approved",
            "priority": "High",
            "due_date": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d"),
            "assigned_to": "Marcus Brody (Operations Mgr)",
            "delayed": False,
            "delay_reason": None,
            "amount": 47900.00
        },
        {
            "sap_id": "PO-4500109501",
            "title": "Corporate Office Laptop Refresh",
            "description": "Standard lease deployment of 150 designer workstations for product development team.",
            "department": "Procurement",
            "status": "Pending",
            "priority": "Medium",
            "due_date": (datetime.now() + timedelta(days=8)).strftime("%Y-%m-%d"),
            "assigned_to": "Sarah Jenkins (Head of Purchasing)",
            "delayed": False,
            "delay_reason": None,
            "amount": 210000.00
        },
        {
            "sap_id": "PO-4500109556",
            "title": "Software License Agreement",
            "description": "Enterprise cloud hosting contract renewal for customer analytics service.",
            "department": "Legal",
            "status": "Delayed",
            "priority": "Critical",
            "due_date": (datetime.now() - timedelta(days=4)).strftime("%Y-%m-%d"),
            "assigned_to": "Elena Rostova (Compliance Counsel)",
            "delayed": True,
            "delay_reason": "Disagreements over data sovereignty indemnity clauses in schedule 4. Vendor refusing arbitration.",
            "amount": 630000.00
        },
        {
            "sap_id": "PO-4500109612",
            "title": "Forklift Fleet Maintenance",
            "description": "Scheduled yearly service contract for warehouse handling equipment.",
            "department": "Warehouse",
            "status": "Approved",
            "priority": "Low",
            "due_date": (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d"),
            "assigned_to": "Marcus Brody (Operations Mgr)",
            "delayed": False,
            "delay_reason": None,
            "amount": 8900.00
        }
    ]

    for t_data in mock_tasks:
        db_task = Task(**t_data)
        db.add(db_task)
        db.commit()
        db.refresh(db_task)

        # Add initial audit log
        audit1 = AuditLog(
            task_id=db_task.id,
            action="Created",
            performed_by="ERP System",
            timestamp=datetime.utcnow() - timedelta(days=7),
            details=f"SAP business document {db_task.sap_id} auto-ingested. Value: ₹{db_task.amount:,.2f}"
        )
        db.add(audit1)
        
        if db_task.status == "Approved":
            audit2 = AuditLog(
                task_id=db_task.id,
                action="Approved",
                performed_by="Marcus Brody (Operations Mgr)",
                timestamp=datetime.utcnow() - timedelta(hours=12),
                details="Line items matched. Goods receipt verification complete. Budget cleared."
            )
            db.add(audit2)
        elif db_task.status == "Delayed":
            audit2 = AuditLog(
                task_id=db_task.id,
                action="Delayed Warning",
                performed_by="AI Predictor",
                timestamp=datetime.utcnow() - timedelta(days=2),
                details=f"SLA breach identified. Reason: {db_task.delay_reason}"
            )
            db.add(audit2)
            
        db.commit()

    return {"message": f"Successfully seeded {len(mock_tasks)} tasks and audit history."}
