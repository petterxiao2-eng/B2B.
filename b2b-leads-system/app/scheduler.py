"""
定时任务调度：每天自动对所有激活项目跑一轮搜索。
生产环境建议：把调度频率、每次搜索的max_results 设置得保守一些，
避免SerpAPI额度/官网请求量激增（比如设置成每天1-2次，而不是每小时）。
"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import settings
from app.database import SessionLocal
from app import models
from app.routers.search import _run_search_pipeline

logger = logging.getLogger("scheduler")

scheduler = BackgroundScheduler()


def scheduled_search_all_projects():
    db = SessionLocal()
    try:
        projects = db.query(models.Project).filter_by(is_active=True).all()
        for project in projects:
            keyword_sets = db.query(models.KeywordSet).filter_by(project_id=project.id, is_active=True).all()
            if not keyword_sets:
                continue
            task = models.SearchTask(project_id=project.id, status=models.TaskStatus.PENDING)
            db.add(task)
            db.commit()
            db.refresh(task)
            logger.info(f"定时任务启动: project={project.name} task_id={task.id}")
            _run_search_pipeline(task.id, [ks.id for ks in keyword_sets], max_results=20)
    finally:
        db.close()


def start_scheduler():
    if not settings.scheduler_enabled:
        logger.info("定时任务未启用（SCHEDULER_ENABLED=false）")
        return
    # 默认每天早上6点（服务器时区）跑一次全量搜索，可根据需要改成多个时间点
    scheduler.add_job(
        scheduled_search_all_projects,
        CronTrigger(hour=6, minute=0),
        id="daily_search_all_projects",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("定时调度器已启动：每天06:00自动搜索所有激活项目")
