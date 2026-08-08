"""Contact management API routes."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.models.contact import Contact
from app.schemas.contact import (
    ContactCreate, ContactUpdate, ContactResponse, ContactListResponse
)

router = APIRouter(prefix="/api/contacts", tags=["contacts"])


@router.get("", response_model=ContactListResponse)
async def list_contacts(
    company_id: Optional[str] = None,
    project_id: Optional[str] = None,
    contact_grade: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """List contacts with filtering."""
    query = select(Contact)
    count_query = select(func.count(Contact.id))

    if company_id:
        query = query.where(Contact.company_id == company_id)
        count_query = count_query.where(Contact.company_id == company_id)
    if project_id:
        query = query.where(Contact.project_id == project_id)
        count_query = count_query.where(Contact.project_id == project_id)
    if contact_grade:
        query = query.where(Contact.contact_grade == contact_grade)
        count_query = count_query.where(Contact.contact_grade == contact_grade)
    if search:
        search_filter = or_(
            Contact.full_name.ilike(f"%{search}%"),
            Contact.job_title.ilike(f"%{search}%"),
            Contact.company_name.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
        count_query = count_query.where(search_filter)

    total = (await db.execute(count_query)).scalar() or 0
    query = query.order_by(Contact.contact_grade.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    contacts = result.scalars().all()

    return ContactListResponse(
        contacts=[ContactResponse.model_validate(c) for c in contacts],
        total=total
    )


@router.post("", response_model=ContactResponse)
async def create_contact(data: ContactCreate, db: AsyncSession = Depends(get_db)):
    """Create a new contact."""
    contact = Contact(**data.model_dump())

    # Auto-assign grade based on available info
    if not contact.contact_grade:
        contact.contact_grade = _auto_grade_contact(contact)

    db.add(contact)
    await db.flush()
    await db.refresh(contact)
    return ContactResponse.model_validate(contact)


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(contact_id: str, db: AsyncSession = Depends(get_db)):
    """Get contact details."""
    result = await db.execute(select(Contact).where(Contact.id == contact_id))
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    return ContactResponse.model_validate(contact)


@router.put("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: str, data: ContactUpdate, db: AsyncSession = Depends(get_db)
):
    """Update contact information."""
    result = await db.execute(select(Contact).where(Contact.id == contact_id))
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(contact, key, value)

    contact.updated_at = datetime.utcnow()
    await db.flush()
    await db.refresh(contact)
    return ContactResponse.model_validate(contact)


@router.delete("/{contact_id}")
async def delete_contact(contact_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a contact."""
    result = await db.execute(select(Contact).where(Contact.id == contact_id))
    contact = result.scalar_one_or_none()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    await db.delete(contact)
    return {"message": "Contact deleted successfully"}


def _auto_grade_contact(contact: Contact) -> str:
    """Auto-grade contact based on available information."""
    has_name = bool(contact.full_name)
    has_title = bool(contact.job_title)
    has_email = bool(contact.personal_email and contact.email_status in ("public", "verified"))
    has_phone = bool(contact.personal_phone)
    has_linkedin = bool(contact.linkedin_personal)

    if has_name and has_title and (has_email or has_phone):
        return "GOLD"
    elif has_name and has_title and (has_linkedin or bool(contact.company_phone)):
        return "SILVER"
    else:
        return "BRONZE"
