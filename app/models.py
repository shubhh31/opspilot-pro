from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Date
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    sap_id = Column(String, index=True, nullable=True) # e.g. "PO-4500108922"
    title = Column(String, index=True)
    description = Column(String, nullable=True)
    department = Column(String, index=True) # Procurement, Warehouse, Finance, Legal, etc.
    status = Column(String, default="Pending") # Pending, In Progress, Approved, Rejected, Delayed
    priority = Column(String, default="Medium") # Low, Medium, High, Critical
    due_date = Column(String) # YYYY-MM-DD format
    assigned_to = Column(String) # Employee Name or Role
    created_at = Column(DateTime, default=datetime.utcnow)
    delayed = Column(Boolean, default=False)
    delay_reason = Column(String, nullable=True)
    amount = Column(Float, default=0.0) # Monetary value involved

    # Relationships
    audit_logs = relationship("AuditLog", back_populates="task", cascade="all, delete-orphan")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=True)
    action = Column(String) # e.g., "Created", "Approved", "Status Change", "AI Scan"
    performed_by = Column(String) # "System", "Manager Name", "AI Copilot"
    timestamp = Column(DateTime, default=datetime.utcnow)
    details = Column(String, nullable=True)

    # Relationships
    task = relationship("Task", back_populates="audit_logs")
