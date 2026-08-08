"""Celery worker entry point for background task execution.

This module defines the Celery application and tasks for the B2B customer
growth system. It handles:
- Google search task execution
- Website background check execution
- Contact research execution
- Batch scoring execution
- Scheduled job management

Usage:
    # Start worker
    celery -A backend.app.worker worker --loglevel=info

    # Start beat scheduler
    celery -A backend.app.worker beat --loglevel=info
"""
import asyncio
import os
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Check if Celery is available
try:
    from celery import Celery
    from celery.schedules import crontab

    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    logger.warning("Celery not installed. Background tasks will run synchronously.")


def create_celery_app() -> Optional["Celery"]:
    """Create and configure Celery application."""
    if not CELERY_AVAILABLE:
        return None

    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    app = Celery(
        "b2b_growth",
        broker=redis_url,
        backend=redis_url,
        include=["backend.app.worker"],
    )

    # Configuration
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        task_time_limit=3600,  # 1 hour max per task
        task_soft_time_limit=3000,  # 50 min soft limit
        worker_prefetch_multiplier=1,
        worker_max_tasks_per_child=100,
        beat_schedule={
            # Auto-search every 6 hours
            "auto-search-6h": {
                "task": "backend.app.worker.run_scheduled_search",
                "schedule": crontab(minute=0, hour="*/6"),
            },
            # Clean up old completed tasks daily
            "cleanup-old-tasks": {
                "task": "backend.app.worker.cleanup_old_tasks",
                "schedule": crontab(minute=0, hour=3),
            },
            # Refresh proxy status every 30 minutes
            "refresh-proxy-status": {
                "task": "backend.app.worker.refresh_proxy_pool",
                "schedule": crontab(minute="*/30"),
            },
        },
    )

    return app


# Create Celery app instance
celery_app = create_celery_app()


def run_async(coro):
    """Run async function from sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, coro)
                return future.result()
        else:
            return loop.run_until_complete(coro)
    except RuntimeError:
        return asyncio.run(coro)


# ============================================================
# Celery Tasks
# ============================================================

if CELERY_AVAILABLE and celery_app:

    @celery_app.task(bind=True, name="backend.app.worker.execute_search_task",
                     max_retries=3, default_retry_delay=60)
    def execute_search_task(self, task_id: str):
        """Execute a Google search task.

        Args:
            task_id: UUID of the SearchTask to execute
        """
        logger.info(f"Executing search task: {task_id}")

        async def _run():
            from app.database import async_session_factory
            from app.services.task_worker import execute_search_task as _exec

            async with async_session_factory() as db:
                await _exec(db, task_id)

        try:
            run_async(_run())
            logger.info(f"Search task completed: {task_id}")
        except Exception as exc:
            logger.error(f"Search task failed: {task_id} - {exc}")
            raise self.retry(exc=exc)

    @celery_app.task(bind=True, name="backend.app.worker.execute_background_check",
                     max_retries=2, default_retry_delay=120)
    def execute_background_check(self, company_id: str):
        """Execute website background check for a company.

        Args:
            company_id: UUID of the Company to check
        """
        logger.info(f"Executing background check: {company_id}")

        async def _run():
            from app.database import async_session_factory
            from app.services.task_worker import execute_background_check as _exec

            async with async_session_factory() as db:
                await _exec(db, company_id)

        try:
            run_async(_run())
            logger.info(f"Background check completed: {company_id}")
        except Exception as exc:
            logger.error(f"Background check failed: {company_id} - {exc}")
            raise self.retry(exc=exc)

    @celery_app.task(bind=True, name="backend.app.worker.execute_contact_research",
                     max_retries=2, default_retry_delay=120)
    def execute_contact_research(self, company_id: str):
        """Execute contact research for a company.

        Args:
            company_id: UUID of the Company to research
        """
        logger.info(f"Executing contact research: {company_id}")

        async def _run():
            from app.database import async_session_factory
            from app.services.task_worker import execute_contact_research as _exec

            async with async_session_factory() as db:
                await _exec(db, company_id)

        try:
            run_async(_run())
            logger.info(f"Contact research completed: {company_id}")
        except Exception as exc:
            logger.error(f"Contact research failed: {company_id} - {exc}")
            raise self.retry(exc=exc)

    @celery_app.task(name="backend.app.worker.execute_batch_score")
    def execute_batch_score(project_id: str):
        """Execute batch scoring for all unscored companies in a project.

        Args:
            project_id: UUID of the Project
        """
        logger.info(f"Executing batch score for project: {project_id}")

        async def _run():
            from app.database import async_session_factory
            from app.services.task_worker import execute_batch_score as _exec

            async with async_session_factory() as db:
                await _exec(db, project_id)

        try:
            run_async(_run())
            logger.info(f"Batch score completed for project: {project_id}")
        except Exception as exc:
            logger.error(f"Batch score failed: {project_id} - {exc}")

    @celery_app.task(name="backend.app.worker.run_scheduled_search")
    def run_scheduled_search():
        """Run scheduled search for all active projects."""
        logger.info("Running scheduled search for active projects")

        async def _run():
            from app.database import async_session_factory
            from app.models.project import Project
            from app.services.task_worker import execute_search_task
            from app.models.task import SearchTask
            from sqlalchemy import select

            async with async_session_factory() as db:
                result = await db.execute(
                    select(Project).where(Project.status == "active")
                )
                projects = result.scalars().all()

                for project in projects:
                    # Create a search task for each active project
                    task = SearchTask(
                        project_id=project.id,
                        task_type="google_search",
                        status="pending",
                    )
                    db.add(task)
                    await db.flush()
                    await execute_search_task(db, str(task.id))
                    logger.info(f"Scheduled search created for project: {project.name}")

                await db.commit()

        try:
            run_async(_run())
        except Exception as exc:
            logger.error(f"Scheduled search failed: {exc}")

    @celery_app.task(name="backend.app.worker.cleanup_old_tasks")
    def cleanup_old_tasks():
        """Clean up completed tasks older than 7 days."""
        logger.info("Cleaning up old completed tasks")

        async def _run():
            from app.database import async_session_factory
            from app.models.task import SearchTask
            from sqlalchemy import select, delete
            from datetime import timedelta

            cutoff = datetime.utcnow() - timedelta(days=7)

            async with async_session_factory() as db:
                await db.execute(
                    delete(SearchTask).where(
                        SearchTask.status.in_(["completed", "failed"]),
                        SearchTask.created_at < cutoff,
                    )
                )
                await db.commit()
                logger.info("Old tasks cleaned up")

        try:
            run_async(_run())
        except Exception as exc:
            logger.error(f"Task cleanup failed: {exc}")

    @celery_app.task(name="backend.app.worker.refresh_proxy_pool")
    def refresh_proxy_pool():
        """Refresh proxy pool health status."""
        logger.info("Refreshing proxy pool status")
        # This would integrate with a proxy service API
        # For now, it's a placeholder
