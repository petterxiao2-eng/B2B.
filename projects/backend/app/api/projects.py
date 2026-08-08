"""Project management API routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.models.project import Project
from app.models.company import Company
from app.schemas.project import (
    ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse
)

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """List all projects with customer counts."""
    query = select(Project)
    if status:
        query = query.where(Project.status == status)
    query = query.offset(skip).limit(limit).order_by(Project.updated_at.desc())

    result = await db.execute(query)
    projects = result.scalars().all()

    # Count customers per project
    project_list = []
    for p in projects:
        count_q = select(func.count(Company.id)).where(Company.project_id == p.id)
        total_result = await db.execute(count_q)
        total = total_result.scalar() or 0

        a_count_q = select(func.count(Company.id)).where(
            Company.project_id == p.id, Company.grade == "A"
        )
        a_result = await db.execute(a_count_q)
        a_grade = a_result.scalar() or 0

        resp = ProjectResponse(
            id=p.id, name=p.name, product_name=p.product_name,
            product_name_en=p.product_name_en, product_description=p.product_description,
            target_markets=p.target_markets, priority_customer_types=p.priority_customer_types,
            delivery_mode=p.delivery_mode, key_advantages=p.key_advantages,
            target_quantity=p.target_quantity, status=p.status,
            last_run_at=p.last_run_at, created_at=p.created_at, updated_at=p.updated_at,
            total_customers=total, a_grade_customers=a_grade
        )
        project_list.append(resp)

    total_q = select(func.count(Project.id))
    if status:
        total_q = total_q.where(Project.status == status)
    total_count = (await db.execute(total_q)).scalar() or 0

    return ProjectListResponse(projects=project_list, total=total_count)


@router.post("", response_model=ProjectResponse)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db)
):
    """Create a new customer development project."""
    project = Project(**data.model_dump())

    # Auto-generate keyword matrix if not provided
    if not project.keyword_matrix:
        project.keyword_matrix = _generate_keyword_matrix(data)

    db.add(project)
    await db.flush()
    await db.refresh(project)

    return ProjectResponse(
        id=project.id, name=project.name, product_name=project.product_name,
        product_name_en=project.product_name_en, product_description=project.product_description,
        target_markets=project.target_markets, priority_customer_types=project.priority_customer_types,
        delivery_mode=project.delivery_mode, key_advantages=project.key_advantages,
        target_quantity=project.target_quantity, status=project.status,
        last_run_at=project.last_run_at, created_at=project.created_at, updated_at=project.updated_at,
        total_customers=0, a_grade_customers=0
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Get project details with customer counts."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    total = (await db.execute(
        select(func.count(Company.id)).where(Company.project_id == project_id)
    )).scalar() or 0
    a_grade = (await db.execute(
        select(func.count(Company.id)).where(Company.project_id == project_id, Company.grade == "A")
    )).scalar() or 0

    return ProjectResponse(
        id=project.id, name=project.name, product_name=project.product_name,
        product_name_en=project.product_name_en, product_description=project.product_description,
        target_markets=project.target_markets, priority_customer_types=project.priority_customer_types,
        delivery_mode=project.delivery_mode, key_advantages=project.key_advantages,
        target_quantity=project.target_quantity, status=project.status,
        last_run_at=project.last_run_at, created_at=project.created_at, updated_at=project.updated_at,
        total_customers=total, a_grade_customers=a_grade
    )


@router.put("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str, data: ProjectUpdate, db: AsyncSession = Depends(get_db)
):
    """Update project configuration."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)

    project.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(project)

    total = (await db.execute(
        select(func.count(Company.id)).where(Company.project_id == project_id)
    )).scalar() or 0
    a_grade = (await db.execute(
        select(func.count(Company.id)).where(Company.project_id == project_id, Company.grade == "A")
    )).scalar() or 0

    return ProjectResponse(
        id=project.id, name=project.name, product_name=project.product_name,
        product_name_en=project.product_name_en, product_description=project.product_description,
        target_markets=project.target_markets, priority_customer_types=project.priority_customer_types,
        delivery_mode=project.delivery_mode, key_advantages=project.key_advantages,
        target_quantity=project.target_quantity, status=project.status,
        last_run_at=project.last_run_at, created_at=project.created_at, updated_at=project.updated_at,
        total_customers=total, a_grade_customers=a_grade
    )


@router.delete("/{project_id}")
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a project and all associated data."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Delete associated companies and contacts
    from app.models.contact import Contact
    await db.execute(
        Contact.__table__.delete().where(Contact.project_id == project_id)
    )
    await db.execute(
        Company.__table__.delete().where(Company.project_id == project_id)
    )
    await db.delete(project)
    return {"message": "Project deleted successfully"}


def _generate_keyword_matrix(data: ProjectCreate) -> dict:
    """Auto-generate keyword matrix based on project config."""
    product_kw = [data.product_name]
    if data.product_name_en:
        product_kw.append(data.product_name_en)

    customer_type_kw = data.priority_customer_types or [
        "distributor", "importer", "wholesaler", "dealer",
        "manufacturer", "OEM", "private label", "retailer",
        "installer", "supplier", "brand owner"
    ]

    evidence_kw = [
        "warehouse", "wholesale", "catalog", "locations",
        "dealer program", "supplier", "procurement",
        "private label", "in stock", "manufacturing"
    ]

    region_kw = data.target_markets or []

    return {
        "product_keywords": product_kw,
        "customer_type_keywords": customer_type_kw,
        "scenario_keywords": [],
        "evidence_keywords": evidence_kw,
        "region_keywords": region_kw
    }
