from fastapi import APIRouter
from sqlalchemy.orm import Session
from collections import defaultdict, Counter

from app.database import SessionLocal
from app.models import Task

router = APIRouter(prefix="/api/reports", tags=["Reports & ML"])

GBTL_DEPARTMENTS = [
    "IT Department",
    "Finance Department",
    "Legal Department",
    "Procurement Department",
    "Production Department",
    "Quality Control Department",
    "Warehouse & Dispatch",
    "HR & Admin Department"
]


def get_tasks():
    db: Session = SessionLocal()
    try:
        return db.query(Task).all()
    finally:
        db.close()


def get_amount(task):
    value = getattr(task, "amount", 0)
    try:
        return float(value or 0)
    except:
        return 0


@router.get("/summary")
def report_summary():
    tasks = get_tasks()

    total = len(tasks)
    delayed = sum(1 for t in tasks if str(t.status).lower() == "delayed")
    pending = sum(1 for t in tasks if str(t.status).lower() == "pending")
    approved = sum(
        1 for t in tasks
        if str(t.status).lower() in ["approved", "resolved", "completed"]
    )

    total_impact = sum(get_amount(t) for t in tasks)
    delayed_impact = sum(
        get_amount(t) for t in tasks
        if str(t.status).lower() == "delayed"
    )

    dept_delay = Counter()
    for t in tasks:
        if str(t.status).lower() == "delayed":
            dept_delay[t.department] += 1

    top_bottleneck = dept_delay.most_common(1)[0][0] if dept_delay else "No major bottleneck"

    return {
        "total_workflows": total,
        "delayed_workflows": delayed,
        "pending_workflows": pending,
        "approved_workflows": approved,
        "total_impact": int(total_impact),
        "delayed_impact": int(delayed_impact),
        "top_bottleneck": top_bottleneck
    }


@router.get("/charts")
def report_charts():
    tasks = get_tasks()

    delay_by_dept = defaultdict(int)
    impact_by_dept = defaultdict(float)
    status_count = defaultdict(int)
    risk_score = defaultdict(int)

    for dept in GBTL_DEPARTMENTS:
        delay_by_dept[dept] = 0
        impact_by_dept[dept] = 0
        risk_score[dept] = 0

    for t in tasks:
        dept = t.department or "Unknown"
        status = str(t.status or "Unknown")
        priority = str(getattr(t, "priority", "") or "").lower()
        amount = get_amount(t)

        status_count[status] += 1
        impact_by_dept[dept] += amount

        if status.lower() == "delayed":
            delay_by_dept[dept] += 1
            risk_score[dept] += 40

        if priority == "high":
            risk_score[dept] += 25
        elif priority == "medium":
            risk_score[dept] += 15
        else:
            risk_score[dept] += 5

        if amount >= 100000:
            risk_score[dept] += 20

    department_risk = [
        {"department": dept, "riskScore": min(score, 100)}
        for dept, score in sorted(risk_score.items(), key=lambda x: x[1], reverse=True)
    ]

    department_delay = [
        {"department": dept, "delayed": count}
        for dept, count in sorted(delay_by_dept.items(), key=lambda x: x[1], reverse=True)
    ]

    department_impact = [
        {"department": dept, "impact": int(value)}
        for dept, value in sorted(impact_by_dept.items(), key=lambda x: x[1], reverse=True)
    ]

    status_distribution = [
        {"status": status, "count": count}
        for status, count in status_count.items()
    ]

    return {
        "department_risk": department_risk,
        "department_delay": department_delay,
        "department_impact": department_impact,
        "status_distribution": status_distribution
    }


@router.get("/predictions")
def ml_predictions():
    tasks = get_tasks()
    predictions = []

    for t in tasks:
        score = 15
        reasons = []

        status = str(t.status or "").lower()
        priority = str(getattr(t, "priority", "") or "").lower()
        amount = get_amount(t)

        if status == "delayed":
            score += 40
            reasons.append("Already delayed")

        if status == "pending":
            score += 20
            reasons.append("Still pending")

        if priority == "high":
            score += 25
            reasons.append("High priority workflow")

        if amount >= 100000:
            score += 20
            reasons.append("High rupee impact")

        if t.department in ["Production Department", "Finance Department", "Procurement Department"]:
            score += 15
            reasons.append("Critical business department")

        score = min(score, 95)

        predictions.append({
            "task_id": t.id,
            "title": t.title,
            "department": t.department,
            "delay_risk": score,
            "risk_level": "High" if score >= 70 else "Medium" if score >= 40 else "Low",
            "reasons": reasons
        })

    predictions = sorted(predictions, key=lambda x: x["delay_risk"], reverse=True)

    return {
        "model": "Rule-based ML simulation",
        "note": "Prediction is based on status, priority, department criticality and rupee impact.",
        "predictions": predictions[:10]
    }


@router.get("/management")
def management_report():
    summary = report_summary()
    charts = report_charts()
    predictions = ml_predictions()

    top_risk = charts["department_risk"][0] if charts["department_risk"] else None
    top_impact = charts["department_impact"][0] if charts["department_impact"] else None
    top_prediction = predictions["predictions"][0] if predictions["predictions"] else None

    report = f"""
Executive Management Report - GBTL Operations

Current workflow count: {summary["total_workflows"]}
Delayed workflows: {summary["delayed_workflows"]}
Pending workflows: {summary["pending_workflows"]}
Total rupee impact: ₹{summary["total_impact"]:,}
Delayed rupee impact: ₹{summary["delayed_impact"]:,}

Top bottleneck department:
{summary["top_bottleneck"]}

Chart reading:
The department risk view indicates that {top_risk["department"] if top_risk else "no department"} currently has the highest operational risk score.
The rupee impact view indicates that {top_impact["department"] if top_impact else "no department"} has the highest financial exposure.

ML prediction:
The highest predicted delay risk is for "{top_prediction["title"] if top_prediction else "no task"}" with risk score {top_prediction["delay_risk"] if top_prediction else 0}%.

Recommended actions:
1. Prioritize delayed and high-value workflows first.
2. Escalate Production, Finance, and Procurement delays.
3. Clear pending approvals before they become SLA breaches.
4. Review high rupee impact tasks above ₹1,00,000.
5. Use Excel scanner before uploading SAP/export data into reports.
"""

    return {
        "title": "GBTL Executive Management Report",
        "report": report.strip()
    }