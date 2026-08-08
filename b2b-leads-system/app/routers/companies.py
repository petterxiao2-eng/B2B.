from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.services.normalize import extract_domain, normalize_phone, check_email_valid

router = APIRouter(prefix="/api/projects/{project_id}/companies", tags=["companies"])


@router.get("", response_model=list[schemas.CompanyOut])
def list_companies(
    project_id: int,
    grade: Optional[str] = Query(None, description="按等级筛选: A/B/C/D"),
    region_code: Optional[str] = Query(None),
    min_score: Optional[float] = Query(None),
    exclude_duplicates: bool = Query(True),
    db: Session = Depends(get_db),
):
    q = db.query(models.Company).filter_by(project_id=project_id)
    if grade:
        q = q.filter(models.Company.grade == grade)
    if region_code:
        q = q.filter(models.Company.region_code == region_code)
    if min_score is not None:
        q = q.filter(models.Company.score_total >= min_score)
    if exclude_duplicates:
        q = q.filter(models.Company.is_duplicate == False)  # noqa: E712
    return q.order_by(models.Company.score_total.desc()).all()


@router.get("/stats")
def company_stats(project_id: int, db: Session = Depends(get_db)):
    """统一口径统计：真实客户数（DB 去重后）= 前端显示数 = 导出数；search_hits 为最近任务的原始搜索命中参考值。"""
    total = db.query(models.Company).filter_by(project_id=project_id).count()
    real = db.query(models.Company).filter_by(project_id=project_id, is_duplicate=False).count()
    last_task = (
        db.query(models.SearchTask)
        .filter_by(project_id=project_id)
        .order_by(models.SearchTask.created_at.desc())
        .first()
    )
    search_hits = last_task.search_hits if last_task else 0
    return {
        "total_companies": total,
        "real_companies": real,
        "search_hits": search_hits,
    }


@router.get("/{company_id}", response_model=schemas.CompanyOut)
def get_company(project_id: int, company_id: int, db: Session = Depends(get_db)):
    company = db.query(models.Company).filter_by(id=company_id, project_id=project_id).first()
    if not company:
        raise HTTPException(404, "客户不存在")
    return company


@router.post("/manual", response_model=schemas.CompanyOut)
def create_company_manual(project_id: int, payload: schemas.CompanyManualCreate, db: Session = Depends(get_db)):
    """手动录入线索，例如展会现场收集的名片信息"""
    domain = extract_domain(payload.website) if payload.website else ""
    dedup_key = domain or None  # 没填官网就不参与去重判定，避免多条"无官网"线索互相冲突

    existing = None
    if dedup_key:
        existing = db.query(models.Company).filter_by(project_id=project_id, dedup_key=dedup_key).first()
    if existing:
        raise HTTPException(409, f"该域名已存在客户记录: {existing.company_name} (id={existing.id})")

    phone_e164 = normalize_phone(payload.phone, payload.region_code or "US") if payload.phone else ""
    email_valid = check_email_valid(payload.email) if payload.email else None

    company = models.Company(
        project_id=project_id,
        company_name=payload.company_name,
        website=payload.website or "",
        website_domain=domain,
        dedup_key=dedup_key,
        email=payload.email or "",
        email_valid=email_valid,
        phone=payload.phone or "",
        phone_e164=phone_e164,
        address=payload.address or "",
        region_code=payload.region_code or "",
        source_platform="manual",
        source_type="manual",
        source_discovered_from="company_website" if payload.website else "",
        source_url="",
        verified_status="手动录入，未经系统背调核实",
    )
    db.add(company)
    db.flush()  # 拿到 company.id 以便写入 company_contacts / company_sources
    _manual_ct = datetime.utcnow()
    if payload.email:
        db.add(models.CompanyContact(company_id=company.id, contact_type="email", value=payload.email, source_page="手动录入", source_url="手动录入", source_type="manual", crawl_time=_manual_ct, is_primary=True))
    if payload.phone:
        db.add(models.CompanyContact(company_id=company.id, contact_type="phone", value=payload.phone, source_page="手动录入", source_url="手动录入", source_type="manual", crawl_time=_manual_ct, is_primary=False))
    # 手动来源也可追溯
    db.add(models.CompanySource(
        company_id=company.id,
        source_type="manual",
        source_discovered_from="company_website" if payload.website else "",
        source_url="",
        source_keyword="",
        source_country=payload.region_code or "",
        original_keyword="",
        translated_keyword="",
        language="",
        crawl_time=datetime.utcnow(),
        snippet=payload.source_note,
    ))
    db.commit()
    db.refresh(company)
    return company


@router.delete("/{company_id}")
def delete_company(project_id: int, company_id: int, db: Session = Depends(get_db)):
    company = db.query(models.Company).filter_by(id=company_id, project_id=project_id).first()
    if not company:
        raise HTTPException(404, "客户不存在")
    db.delete(company)
    db.commit()
    return {"ok": True}


@router.post("/{company_id}/contacts", response_model=schemas.ContactOut)
def add_contact(project_id: int, company_id: int, name: str, title: str = "", email: str = "",
                 phone: str = "", source_note: str = "手动补充", db: Session = Depends(get_db)):
    company = db.query(models.Company).filter_by(id=company_id, project_id=project_id).first()
    if not company:
        raise HTTPException(404, "客户不存在")
    contact = models.Contact(
        company_id=company_id, name=name, title=title, email=email,
        phone=phone, source_note=source_note,
    )
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact
