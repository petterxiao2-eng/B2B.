"""Pydantic schemas for Project."""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class ProjectCreate(BaseModel):
    name: str = Field(..., max_length=200)
    product_name: str = Field(..., max_length=200)
    product_name_en: Optional[str] = None
    product_description: Optional[str] = None
    target_markets: Optional[List[str]] = None
    target_countries: Optional[List[str]] = None
    priority_customer_types: Optional[List[str]] = None
    delivery_mode: Optional[str] = None
    key_advantages: Optional[str] = None
    target_quantity: int = 100
    keyword_matrix: Optional[dict] = None
    scoring_template: Optional[dict] = None


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    product_name: Optional[str] = None
    product_name_en: Optional[str] = None
    product_description: Optional[str] = None
    target_markets: Optional[List[str]] = None
    target_countries: Optional[List[str]] = None
    priority_customer_types: Optional[List[str]] = None
    delivery_mode: Optional[str] = None
    key_advantages: Optional[str] = None
    target_quantity: Optional[int] = None
    keyword_matrix: Optional[dict] = None
    scoring_template: Optional[dict] = None
    status: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    product_name: str
    product_name_en: Optional[str]
    product_description: Optional[str]
    target_markets: Optional[List[str]]
    priority_customer_types: Optional[List[str]]
    delivery_mode: Optional[str]
    key_advantages: Optional[str]
    target_quantity: int
    status: str
    last_run_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    # Computed fields
    total_customers: int = 0
    a_grade_customers: int = 0

    class Config:
        from_attributes = True


class ProjectListResponse(BaseModel):
    projects: List[ProjectResponse]
    total: int
