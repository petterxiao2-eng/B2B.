"""Pydantic schemas for Contact."""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ContactCreate(BaseModel):
    company_id: str
    project_id: str
    company_name: Optional[str] = None
    full_name: Optional[str] = None
    job_title: Optional[str] = None
    decision_role: Optional[str] = None
    contact_grade: Optional[str] = None
    personal_email: Optional[str] = None
    email_status: Optional[str] = None
    company_email: Optional[str] = None
    personal_phone: Optional[str] = None
    company_phone: Optional[str] = None
    linkedin_personal: Optional[str] = None
    linkedin_company: Optional[str] = None
    identity_source_url: Optional[str] = None
    contact_source_url: Optional[str] = None
    suggested_channel: Optional[str] = None
    research_notes: Optional[str] = None


class ContactUpdate(BaseModel):
    full_name: Optional[str] = None
    job_title: Optional[str] = None
    decision_role: Optional[str] = None
    contact_grade: Optional[str] = None
    personal_email: Optional[str] = None
    email_status: Optional[str] = None
    company_email: Optional[str] = None
    personal_phone: Optional[str] = None
    company_phone: Optional[str] = None
    linkedin_personal: Optional[str] = None
    linkedin_company: Optional[str] = None
    employment_status: Optional[str] = None
    suggested_channel: Optional[str] = None
    research_notes: Optional[str] = None
    review_status: Optional[str] = None


class ContactResponse(BaseModel):
    id: str
    company_id: str
    project_id: str
    company_name: Optional[str]
    full_name: Optional[str]
    job_title: Optional[str]
    decision_role: Optional[str]
    contact_grade: Optional[str]
    personal_email: Optional[str]
    email_status: Optional[str]
    company_email: Optional[str]
    personal_phone: Optional[str]
    company_phone: Optional[str]
    linkedin_personal: Optional[str]
    linkedin_company: Optional[str]
    identity_source_url: Optional[str]
    contact_source_url: Optional[str]
    collected_at: datetime
    employment_status: str
    suggested_channel: Optional[str]
    research_notes: Optional[str]
    review_status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ContactListResponse(BaseModel):
    contacts: List[ContactResponse]
    total: int
