"""Contact model - decision makers for A/B grade companies."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, JSON
from app.database import Base


class Contact(Base):
    __tablename__ = "contacts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    company_id = Column(String(36), nullable=False, index=True)
    project_id = Column(String(36), nullable=False, index=True)

    # Company reference
    company_name = Column(String(300), nullable=True)

    # Contact info
    full_name = Column(String(200), nullable=True)
    job_title = Column(String(200), nullable=True)
    decision_role = Column(String(100), nullable=True)
    # product_manager/buyer/purchasing_manager/supply_chain/owner/founder/engineering

    # Grading
    contact_grade = Column(String(20), nullable=True)  # GOLD/SILVER/BRONZE

    # Email
    personal_email = Column(String(200), nullable=True)
    email_status = Column(String(20), nullable=True)  # public/verified/inferred/unknown
    company_email = Column(String(200), nullable=True)

    # Phone
    personal_phone = Column(String(50), nullable=True)  # E.164 format
    company_phone = Column(String(50), nullable=True)

    # Social
    linkedin_personal = Column(String(500), nullable=True)
    linkedin_company = Column(String(500), nullable=True)

    # Sources
    identity_source_url = Column(String(500), nullable=True)
    contact_source_url = Column(String(500), nullable=True)
    collected_at = Column(DateTime, default=datetime.utcnow)

    # Status
    employment_status = Column(String(20), default="active")  # active/former/unknown
    suggested_channel = Column(String(50), nullable=True)  # email/linkedin/whatsapp/phone
    research_notes = Column(Text, nullable=True)

    # Review
    review_status = Column(String(20), default="pending")
    reviewed_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
