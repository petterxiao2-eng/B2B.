"""Pydantic schemas for Company/Customer."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class CompanyCreate(BaseModel):
    project_id: str
    company_name: str
    website: Optional[str] = None
    country: Optional[str] = None
    state_province: Optional[str] = None
    city: Optional[str] = None
    customer_type: Optional[str] = None
    main_business: Optional[str] = None
    related_products: Optional[str] = None
    product_match_evidence: Optional[str] = None
    procurement_capability: Optional[str] = None
    inventory_channel_capability: Optional[str] = None
    discovery_path: Optional[str] = None
    source_keywords: Optional[str] = None
    source_url_1: Optional[str] = None
    source_url_2: Optional[str] = None


class CompanyUpdate(BaseModel):
    company_name: Optional[str] = None
    website: Optional[str] = None
    country: Optional[str] = None
    state_province: Optional[str] = None
    city: Optional[str] = None
    customer_type: Optional[str] = None
    customer_pool: Optional[str] = None
    main_business: Optional[str] = None
    related_products: Optional[str] = None
    product_match_evidence: Optional[str] = None
    procurement_capability: Optional[str] = None
    inventory_channel_capability: Optional[str] = None
    score: Optional[float] = None
    score_details: Optional[dict] = None
    grade: Optional[str] = None
    review_status: Optional[str] = None
    background_report: Optional[dict] = None
    whatsapp_numbers: Optional[List[str]] = None
    whatsapp_group_links: Optional[List[str]] = None
    customs_data: Optional[dict] = None
    suggested_approach: Optional[str] = None
    items_to_verify: Optional[str] = None


class CompanyResponse(BaseModel):
    id: str
    project_id: str
    company_name: str
    website: Optional[str]
    country: Optional[str]
    state_province: Optional[str]
    city: Optional[str]
    customer_type: Optional[str]
    customer_pool: Optional[str]
    main_business: Optional[str]
    related_products: Optional[str]
    product_match_evidence: Optional[str]
    procurement_capability: Optional[str]
    inventory_channel_capability: Optional[str]
    score: float
    score_details: Optional[dict]
    grade: Optional[str]
    discovery_path: Optional[str]
    source_keywords: Optional[str]
    source_url_1: Optional[str]
    source_url_2: Optional[str]
    collected_at: datetime
    suggested_approach: Optional[str]
    items_to_verify: Optional[str]
    review_status: str
    background_report: Optional[dict]
    whatsapp_numbers: Optional[List[str]]
    whatsapp_group_links: Optional[List[str]]
    customs_data: Optional[dict]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CompanyListResponse(BaseModel):
    companies: List[CompanyResponse]
    total: int
    page: int
    page_size: int


class CompanyFilter(BaseModel):
    project_id: Optional[str] = None
    grade: Optional[str] = None
    country: Optional[str] = None
    customer_type: Optional[str] = None
    review_status: Optional[str] = None
    min_score: Optional[float] = None
    search: Optional[str] = None
