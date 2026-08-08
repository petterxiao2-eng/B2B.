"""Dashboard overview API - aggregated stats."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.project import Project
from app.models.company import Company
from app.models.contact import Contact
from app.models.task import SearchTask, DraftMessage

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    """Get aggregated dashboard statistics."""
    total_projects = (await db.execute(select(func.count(Project.id)))).scalar() or 0
    active_projects = (await db.execute(
        select(func.count(Project.id)).where(Project.status == "active")
    )).scalar() or 0

    total_companies = (await db.execute(select(func.count(Company.id)))).scalar() or 0
    a_grade = (await db.execute(
        select(func.count(Company.id)).where(Company.grade == "A")
    )).scalar() or 0
    b_grade = (await db.execute(
        select(func.count(Company.id)).where(Company.grade == "B")
    )).scalar() or 0
    c_grade = (await db.execute(
        select(func.count(Company.id)).where(Company.grade == "C")
    )).scalar() or 0
    d_grade = (await db.execute(
        select(func.count(Company.id)).where(Company.grade == "D")
    )).scalar() or 0

    total_contacts = (await db.execute(select(func.count(Contact.id)))).scalar() or 0
    gold_contacts = (await db.execute(
        select(func.count(Contact.id)).where(Contact.contact_grade == "GOLD")
    )).scalar() or 0
    silver_contacts = (await db.execute(
        select(func.count(Contact.id)).where(Contact.contact_grade == "SILVER")
    )).scalar() or 0

    pending_tasks = (await db.execute(
        select(func.count(SearchTask.id)).where(SearchTask.status == "pending")
    )).scalar() or 0
    running_tasks = (await db.execute(
        select(func.count(SearchTask.id)).where(SearchTask.status == "running")
    )).scalar() or 0

    pending_drafts = (await db.execute(
        select(func.count(DraftMessage.id)).where(DraftMessage.status == "draft")
    )).scalar() or 0

    # Country distribution
    country_q = select(Company.country, func.count(Company.id)).group_by(Company.country).order_by(
        func.count(Company.id).desc()
    ).limit(10)
    country_result = await db.execute(country_q)
    country_dist = [{"country": r[0] or "Unknown", "count": r[1]} for r in country_result.all()]

    # Grade distribution
    grade_dist = [
        {"grade": "A", "count": a_grade, "label": "Priority"},
        {"grade": "B", "count": b_grade, "label": "Developable"},
        {"grade": "C", "count": c_grade, "label": "Watch"},
        {"grade": "D", "count": d_grade, "label": "Low Priority"},
    ]

    return {
        "projects": {
            "total": total_projects,
            "active": active_projects
        },
        "companies": {
            "total": total_companies,
            "by_grade": grade_dist,
            "by_country": country_dist
        },
        "contacts": {
            "total": total_contacts,
            "gold": gold_contacts,
            "silver": silver_contacts,
            "bronze": total_contacts - gold_contacts - silver_contacts
        },
        "tasks": {
            "pending": pending_tasks,
            "running": running_tasks
        },
        "drafts": {
            "pending_review": pending_drafts
        }
    }


@router.get("/recent-activity")
async def get_recent_activity(db: AsyncSession = Depends(get_db)):
    """Get recent activity feed."""
    activities = []

    # Recent companies
    result = await db.execute(
        select(Company).order_by(Company.created_at.desc()).limit(5)
    )
    for c in result.scalars().all():
        activities.append({
            "type": "company_discovered",
            "message": f"Discovered {c.company_name} ({c.country or 'Unknown'})",
            "grade": c.grade,
            "score": c.score,
            "timestamp": c.created_at.isoformat() if c.created_at else None,
            "company_id": c.id
        })

    # Recent tasks
    result = await db.execute(
        select(SearchTask).order_by(SearchTask.created_at.desc()).limit(5)
    )
    for t in result.scalars().all():
        activities.append({
            "type": "task_completed" if t.status == "completed" else "task_created",
            "message": f"Search task: {t.task_type} - {t.status}",
            "timestamp": t.created_at.isoformat() if t.created_at else None
        })

    activities.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return {"activities": activities[:10]}
