"""SearchTask model - tracks search/crawl tasks in the queue."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, JSON, Float
from app.database import Base


class SearchTask(Base):
    __tablename__ = "search_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), nullable=False, index=True)

    task_type = Column(String(50), nullable=False)
    # google_search/website_scrape/background_check/contact_research/whatsapp_sniff/customs_check

    # Task parameters
    params = Column(JSON, nullable=True)
    # For google_search: {"query": "...", "keywords": [...]}
    # For website_scrape: {"company_id": "...", "url": "..."}
    # For background_check: {"company_id": "..."}
    # For contact_research: {"company_id": "..."}

    # Status tracking
    status = Column(String(20), default="pending")
    # pending/running/completed/failed/retry
    priority = Column(Integer, default=5)  # 1=highest, 10=lowest
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    # Results
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Proxy used
    proxy_used = Column(String(200), nullable=True)


class ScheduledJob(Base):
    __tablename__ = "scheduled_jobs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), nullable=False, index=True)
    job_type = Column(String(50), nullable=False)
    cron_expression = Column(String(100), nullable=True)
    interval_hours = Column(Integer, default=24)
    is_active = Column(Integer, default=1)  # 0=inactive, 1=active
    last_run_at = Column(DateTime, nullable=True)
    next_run_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class DraftMessage(Base):
    __tablename__ = "draft_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String(36), nullable=False, index=True)
    contact_id = Column(String(36), nullable=True)
    project_id = Column(String(36), nullable=False, index=True)

    channel = Column(String(20), nullable=False)  # email/whatsapp
    subject = Column(String(500), nullable=True)
    body = Column(Text, nullable=False)

    # Content breakdown
    content_breakdown = Column(JSON, nullable=True)
    # {
    #   "product_capability_pct": 70,
    #   "personalization_pct": 30,
    #   "company_facts": [...],
    #   "match_reason": "",
    #   "products_mentioned": [],
    #   "delivery_advantage": "",
    #   "cta": ""
    # }

    status = Column(String(20), default="draft")  # draft/reviewing/approved/sent/failed
    reviewed_by = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
