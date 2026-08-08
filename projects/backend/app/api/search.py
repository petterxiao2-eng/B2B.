"""Search and task management API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.models.task import SearchTask, ScheduledJob
from app.models.project import Project

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.get("")
async def list_tasks(
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    task_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """List search tasks with filtering."""
    query = select(SearchTask)
    if project_id:
        query = query.where(SearchTask.project_id == project_id)
    if status:
        query = query.where(SearchTask.status == status)
    if task_type:
        query = query.where(SearchTask.task_type == task_type)

    query = query.order_by(SearchTask.priority.asc(), SearchTask.created_at.desc())
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    tasks = result.scalars().all()

    return {
        "tasks": [
            {
                "id": t.id, "project_id": t.project_id, "task_type": t.task_type,
                "params": t.params, "status": t.status, "priority": t.priority,
                "retry_count": t.retry_count, "error_message": t.error_message,
                "started_at": t.started_at.isoformat() if t.started_at else None,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in tasks
        ]
    }


@router.post("/search")
async def trigger_search(
    project_id: str,
    search_type: str = "google_matrix",
    db: AsyncSession = Depends(get_db)
):
    """Trigger a search task for a project."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    task = SearchTask(
        project_id=project_id,
        task_type="google_search",
        params={"search_type": search_type, "keyword_matrix": project.keyword_matrix},
        status="pending",
        priority=5
    )
    db.add(task)

    project.last_run_at = datetime.utcnow()
    await db.flush()
    await db.refresh(task)

    return {
        "message": "Search task created",
        "task_id": task.id,
        "status": task.status
    }


@router.get("/queue/stats")
async def queue_stats(db: AsyncSession = Depends(get_db)):
    """Get task queue statistics."""
    stats = {}
    for status in ["pending", "running", "completed", "failed"]:
        count = (await db.execute(
            select(func.count(SearchTask.id)).where(SearchTask.status == status)
        )).scalar() or 0
        stats[status] = count

    total = sum(stats.values())
    return {"total": total, "by_status": stats}


@router.get("/scheduled")
async def list_scheduled_jobs(
    project_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """List scheduled jobs."""
    query = select(ScheduledJob)
    if project_id:
        query = query.where(ScheduledJob.project_id == project_id)

    result = await db.execute(query)
    jobs = result.scalars().all()

    return {
        "jobs": [
            {
                "id": j.id, "project_id": j.project_id, "job_type": j.job_type,
                "cron_expression": j.cron_expression, "interval_hours": j.interval_hours,
                "is_active": bool(j.is_active), "last_run_at": j.last_run_at,
                "next_run_at": j.next_run_at
            }
            for j in jobs
        ]
    }


@router.post("/scheduled")
async def create_scheduled_job(
    project_id: str,
    job_type: str = "auto_search",
    interval_hours: int = 24,
    db: AsyncSession = Depends(get_db)
):
    """Create a scheduled job."""
    job = ScheduledJob(
        project_id=project_id,
        job_type=job_type,
        interval_hours=interval_hours,
        is_active=1
    )
    db.add(job)
    await db.flush()
    await db.refresh(job)
    return {"message": "Scheduled job created", "job_id": job.id}


@router.get("/proxy/status")
async def proxy_status():
    """Get proxy pool status and health check results.
    
    Returns simulated proxy status for monitoring dashboard.
    In production, this would connect to actual proxy provider APIs.
    """
    import random
    from datetime import datetime, timedelta
    
    # Simulated proxy pool - in production, read from Redis or DB
    proxy_regions = [
        {"region": "US-East", "country": "US", "proxies": 12},
        {"region": "US-West", "country": "US", "proxies": 8},
        {"region": "EU-West", "country": "DE", "proxies": 15},
        {"region": "EU-Central", "country": "FR", "proxies": 10},
        {"region": "Asia-Pacific", "country": "SG", "proxies": 6},
        {"region": "South America", "country": "BR", "proxies": 4},
    ]
    
    pool = []
    now = datetime.utcnow()
    for r in proxy_regions:
        for i in range(r["proxies"]):
            last_check = now - timedelta(minutes=random.randint(0, 30))
            is_healthy = random.random() > 0.15  # 85% healthy
            pool.append({
                "id": f"proxy-{r['country'].lower()}-{i:03d}",
                "region": r["region"],
                "country": r["country"],
                "ip": f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
                "port": random.choice([8080, 3128, 1080, 8888, 9090]),
                "status": "healthy" if is_healthy else "degraded",
                "latency_ms": random.randint(50, 800) if is_healthy else random.randint(1000, 5000),
                "last_check": last_check.isoformat(),
                "success_rate": round(random.uniform(0.7, 1.0) if is_healthy else random.uniform(0.1, 0.5), 2),
                "requests_today": random.randint(0, 500),
            })
    
    total = len(pool)
    healthy = sum(1 for p in pool if p["status"] == "healthy")
    degraded = total - healthy
    avg_latency = sum(p["latency_ms"] for p in pool) / total if total else 0
    
    return {
        "summary": {
            "total": total,
            "healthy": healthy,
            "degraded": degraded,
            "avg_latency_ms": round(avg_latency),
            "health_rate": round(healthy / total, 2) if total else 0,
        },
        "by_region": [
            {
                "region": r["region"],
                "country": r["country"],
                "total": r["proxies"],
                "healthy": sum(1 for p in pool if p["region"] == r["region"] and p["status"] == "healthy"),
            }
            for r in proxy_regions
        ],
        "proxies": pool,
    }
