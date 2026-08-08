from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, ConfigDict


# ---------- Project ----------
class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    target_regions: List[str] = []


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str
    target_regions: List[str]
    is_active: bool
    created_at: datetime


# ---------- KeywordSet ----------
class KeywordSetCreate(BaseModel):
    region_code: str
    product_keywords: List[str]
    dork_filters: List[str] = []
    industry_keywords: List[str] = []
    customer_type_tiers: List[str] = []
    country_profile: str = ""
    language: str = "en"


class KeywordSetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    region_code: str
    product_keywords: List[str]
    dork_filters: List[str]
    industry_keywords: List[str]
    customer_type_tiers: List[str]
    country_profile: str
    language: str
    is_active: bool


# ---------- ScoringTemplate ----------
class ScoringTemplateUpdate(BaseModel):
    weights: Dict[str, float]
    grade_thresholds: Dict[str, float]


# ---------- Company ----------
class ContactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    title: str
    email: str
    phone: str
    source_note: str
    source_url: str
    source_type: str = ""
    crawl_time: Optional[datetime] = None
    is_decision_maker: bool


class CompanyContactOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    contact_type: str
    value: str
    source_page: str
    source_url: str
    source_type: str = ""
    crawl_time: Optional[datetime] = None
    is_primary: bool


class CompanySourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    company_id: int
    source_type: str
    source_discovered_from: str = ""
    source_url: str
    source_keyword: str
    source_country: str
    original_keyword: str
    translated_keyword: str
    language: str
    crawl_time: Optional[datetime]
    snippet: str


class CompanyVerificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    company_id: int
    dns_valid: Optional[bool]
    dns_records: List[str]
    http_status: Optional[int]
    ssl_valid: Optional[bool]
    ssl_issuer: str
    ssl_expiry: str
    mx_valid: Optional[bool]
    mx_records: List[str]
    checked_at: Optional[datetime]


class CompanyScoreOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    company_id: int
    total: float
    grade: str
    breakdown: Dict[str, Any]
    reason: str
    model: str
    computed_at: Optional[datetime]


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    company_name: str
    address: str
    email: str
    email_valid: Optional[bool]
    website: str
    phone: str
    phone_e164: str
    source_url: str
    source_platform: str
    source_type: str
    source_discovered_from: str = ""
    source_keyword: str
    original_keyword: str
    translated_keyword: str
    language: str
    region_code: str
    business_type: str
    products_summary: str
    company_size_estimate: str
    # V2 补齐字段
    whatsapp: str
    linkedin: str
    facebook: str
    purchase_probability: float
    # V2 真实性验证字段
    dns_valid: Optional[bool]
    http_status: Optional[int]
    ssl_valid: Optional[bool]
    mx_valid: Optional[bool]
    # V2 追溯字段
    crawl_time: Optional[datetime]
    original_pages: List[str]
    score_total: float
    grade: str
    score_breakdown: Dict[str, Any]
    score_reason: str
    background_report: Dict[str, Any]
    verified_status: str
    contacts: List[ContactOut] = []
    company_contacts: List[CompanyContactOut] = []
    company_sources: List[CompanySourceOut] = []
    created_at: datetime


class CompanyManualCreate(BaseModel):
    """支持手动录入一条线索（例如展会现场收集的名片）"""
    company_name: str
    website: Optional[str] = ""
    email: Optional[str] = ""
    phone: Optional[str] = ""
    address: Optional[str] = ""
    region_code: Optional[str] = ""
    source_note: str = "手动录入"


# ---------- SearchTask ----------
class SearchTaskTrigger(BaseModel):
    keyword_set_id: Optional[int] = None  # 不传则跑该项目下所有激活的关键词集
    max_results_per_query: int = 20


class CrawlUrlPayload(BaseModel):
    """手动输入一个 URL，直接触发 Company Website / Trade Directory 真实抓取。"""
    url: str
    region_code: str = ""  # 可选，缺省取项目首个目标地区


class SearchTaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    project_id: int
    status: str
    task_type: str = "search"  # search / website / directory
    query_used: str
    results_found: int
    new_companies: int
    search_hits: int
    real_companies: int
    # Search Funnel 漏斗统计
    queries_generated: int = 0
    serp_results: int = 0
    dedup_count: int = 0
    verified_count: int = 0
    error_message: str
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    created_at: datetime


# ---------- Outreach ----------
class OutreachDraftGenerate(BaseModel):
    company_id: int
    channel: str = "email"  # email / whatsapp
    tone: str = "professional"  # professional / friendly / direct


class OutreachDraftOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    company_id: int
    channel: str
    subject: str
    body: str
    status: str
    created_at: datetime
