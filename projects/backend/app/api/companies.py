"""Company/Customer management API routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import Optional
from datetime import datetime
import csv
import io
from fastapi.responses import StreamingResponse

from app.database import get_db
from app.models.company import Company
from app.models.contact import Contact
from app.schemas.company import (
    CompanyCreate, CompanyUpdate, CompanyResponse, CompanyListResponse
)

router = APIRouter(prefix="/api/companies", tags=["companies"])


@router.get("", response_model=CompanyListResponse)
async def list_companies(
    project_id: Optional[str] = None,
    grade: Optional[str] = None,
    country: Optional[str] = None,
    customer_type: Optional[str] = None,
    review_status: Optional[str] = None,
    min_score: Optional[float] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """List companies with filtering and pagination."""
    query = select(Company)
    count_query = select(func.count(Company.id))

    filters = []
    if project_id:
        filters.append(Company.project_id == project_id)
    if grade:
        filters.append(Company.grade == grade)
    if country:
        filters.append(Company.country == country)
    if customer_type:
        filters.append(Company.customer_type == customer_type)
    if review_status:
        filters.append(Company.review_status == review_status)
    if min_score is not None:
        filters.append(Company.score >= min_score)
    if search:
        filters.append(or_(
            Company.company_name.ilike(f"%{search}%"),
            Company.main_business.ilike(f"%{search}%"),
            Company.related_products.ilike(f"%{search}%")
        ))

    for f in filters:
        query = query.where(f)
        count_query = count_query.where(f)

    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(Company.score.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    companies = result.scalars().all()

    return CompanyListResponse(
        companies=[CompanyResponse.model_validate(c) for c in companies],
        total=total, page=page, page_size=page_size
    )


@router.post("", response_model=CompanyResponse)
async def create_company(data: CompanyCreate, db: AsyncSession = Depends(get_db)):
    """Create a new company record."""
    # Dedup check: same project + same domain or company name
    if data.website:
        domain = _extract_domain(data.website)
        existing = await db.execute(
            select(Company).where(
                Company.project_id == data.project_id,
                Company.domain == domain
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Company with same domain already exists")
    else:
        existing = await db.execute(
            select(Company).where(
                Company.project_id == data.project_id,
                Company.company_name == data.company_name
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Company with same name already exists")

    company = Company(**data.model_dump())
    if data.website:
        company.domain = _extract_domain(data.website)

    db.add(company)
    await db.flush()
    await db.refresh(company)
    return CompanyResponse.model_validate(company)


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(company_id: str, db: AsyncSession = Depends(get_db)):
    """Get company details."""
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return CompanyResponse.model_validate(company)


@router.put("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: str, data: CompanyUpdate, db: AsyncSession = Depends(get_db)
):
    """Update company information."""
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(company, key, value)

    company.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(company)
    return CompanyResponse.model_validate(company)


@router.delete("/{company_id}")
async def delete_company(company_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a company and its contacts."""
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    await db.execute(
        Contact.__table__.delete().where(Contact.company_id == company_id)
    )
    await db.delete(company)
    return {"message": "Company deleted successfully"}


@router.get("/{company_id}/contacts")
async def get_company_contacts(company_id: str, db: AsyncSession = Depends(get_db)):
    """Get all contacts for a company."""
    result = await db.execute(
        select(Contact).where(Contact.company_id == company_id).order_by(
            Contact.contact_grade.desc()
        )
    )
    contacts = result.scalars().all()
    return {"contacts": [
        {
            "id": c.id, "full_name": c.full_name, "job_title": c.job_title,
            "decision_role": c.decision_role, "contact_grade": c.contact_grade,
            "personal_email": c.personal_email, "email_status": c.email_status,
            "company_email": c.company_email, "personal_phone": c.personal_phone,
            "company_phone": c.company_phone, "linkedin_personal": c.linkedin_personal,
            "linkedin_company": c.linkedin_company, "suggested_channel": c.suggested_channel,
            "review_status": c.review_status
        }
        for c in contacts
    ]}


@router.get("/export/csv")
async def export_companies_csv(
    project_id: str,
    grade: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Export companies to CSV."""
    query = select(Company).where(Company.project_id == project_id)
    if grade:
        query = query.where(Company.grade == grade)
    query = query.order_by(Company.score.desc())

    result = await db.execute(query)
    companies = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Company Name", "Website", "Country", "City", "Customer Type",
        "Main Business", "Score", "Grade", "Discovery Path", "Source URL"
    ])
    for c in companies:
        writer.writerow([
            c.company_name, c.website, c.country, c.city, c.customer_type,
            c.main_business, c.score, c.grade, c.discovery_path, c.source_url_1
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=companies_{project_id}.csv"}
    )


@router.post("/{company_id}/background-check")
async def trigger_background_check(company_id: str):
    """Trigger AI background check for a company website."""
    from app.services.task_worker import task_worker
    result = await task_worker.execute_background_check(company_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/{company_id}/research-contacts")
async def trigger_contact_research(company_id: str):
    """Trigger decision maker contact research for a company."""
    from app.services.task_worker import task_worker
    result = await task_worker.execute_contact_research(company_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/batch-score")
async def batch_score_companies(
    project_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Trigger batch scoring for all unscored companies in a project."""
    from app.services.task_worker import task_worker
    result = await task_worker.execute_batch_scoring(project_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


def _extract_domain(url: str) -> str:
    """Extract domain from URL for dedup."""
    url = url.lower().strip()
    for prefix in ["https://", "http://", "www."]:
        url = url.removeprefix(prefix)
    return url.split("/")[0].split("?")[0]
