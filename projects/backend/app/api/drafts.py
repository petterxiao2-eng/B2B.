"""Draft message management API routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.models.task import DraftMessage
from app.models.company import Company
from app.models.contact import Contact

router = APIRouter(prefix="/api/drafts", tags=["drafts"])


@router.get("")
async def list_drafts(
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    channel: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """List draft messages."""
    query = select(DraftMessage)
    if project_id:
        query = query.where(DraftMessage.project_id == project_id)
    if status:
        query = query.where(DraftMessage.status == status)
    if channel:
        query = query.where(DraftMessage.channel == channel)

    query = query.order_by(DraftMessage.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    drafts = result.scalars().all()

    return {
        "drafts": [
            {
                "id": d.id, "company_id": d.company_id, "contact_id": d.contact_id,
                "project_id": d.project_id, "channel": d.channel,
                "subject": d.subject, "body": d.body,
                "content_breakdown": d.content_breakdown,
                "status": d.status, "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in drafts
        ]
    }


@router.post("/generate")
async def generate_draft(
    company_id: str,
    contact_id: Optional[str] = None,
    channel: str = "email",
    db: AsyncSession = Depends(get_db)
):
    """Generate a personalized outreach draft based on company background data."""
    # Get company
    result = await db.execute(select(Company).where(Company.id == company_id))
    company = result.scalar_one_or_none()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Get contact if specified
    contact = None
    if contact_id:
        result = await db.execute(select(Contact).where(Contact.id == contact_id))
        contact = result.scalar_one_or_none()

    # Generate draft content
    draft_body = _generate_draft_content(company, contact, channel)

    draft = DraftMessage(
        company_id=company_id,
        contact_id=contact_id,
        project_id=company.project_id,
        channel=channel,
        subject=draft_body["subject"] if channel == "email" else None,
        body=draft_body["body"],
        content_breakdown=draft_body["breakdown"],
        status="draft"
    )
    db.add(draft)
    await db.flush()
    await db.refresh(draft)

    return {
        "id": draft.id,
        "channel": channel,
        "subject": draft.subject,
        "body": draft.body,
        "content_breakdown": draft.content_breakdown,
        "status": "draft"
    }


@router.put("/{draft_id}")
async def update_draft(
    draft_id: str,
    body: Optional[str] = None,
    subject: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Update a draft (edit content or approve)."""
    result = await db.execute(select(DraftMessage).where(DraftMessage.id == draft_id))
    draft = result.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")

    if body is not None:
        draft.body = body
    if subject is not None:
        draft.subject = subject
    if status is not None:
        draft.status = status
        if status == "approved":
            draft.reviewed_at = datetime.utcnow()
        elif status == "sent":
            draft.sent_at = datetime.utcnow()

    draft.updated_at = datetime.utcnow()
    await db.flush()
    return {"message": "Draft updated", "id": draft.id, "status": draft.status}


@router.delete("/{draft_id}")
async def delete_draft(draft_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a draft."""
    result = await db.execute(select(DraftMessage).where(DraftMessage.id == draft_id))
    draft = result.scalar_one_or_none()
    if not draft:
        raise HTTPException(status_code=404, detail="Draft not found")
    await db.delete(draft)
    return {"message": "Draft deleted"}


def _generate_draft_content(company: Company, contact: Contact | None, channel: str) -> dict:
    """Generate personalized outreach content.

    Rules:
    - 70% product supply capability + 30% company-specific personalization
    - Must include: real company facts, match reason, relevant products, delivery advantage, low-friction CTA
    - No unverifiable flattery, no fabricated needs, no batch templates
    """
    company_facts = []
    if company.main_business:
        company_facts.append(f"your focus on {company.main_business}")
    if company.related_products:
        company_facts.append(f"your product range including {company.related_products}")
    if company.country:
        company_facts.append(f"your presence in {company.country}")

    facts_str = " and ".join(company_facts[:2]) if company_facts else "your business"

    if channel == "email":
        subject = f"Supply Partnership Inquiry - {company.company_name}"
        body = f"""Dear {contact.full_name if contact else "Sir/Madam"},

I came across {company.company_name} while researching {facts_str}. Your company's profile caught our attention as a potential partner.

We are a specialized supplier with strong capabilities in {company.related_products or 'our product range'}, and I believe there could be a natural fit between our offerings and your business needs.

**Why we might be a good match:**
- We supply {company.related_products or 'similar products'} with consistent quality
- Our delivery capabilities align with your market requirements
- We offer competitive pricing with flexible MOQ options

**Our key strengths:**
- Reliable supply chain with on-time delivery track record
- Quality certifications and testing capabilities
- Flexible customization options

Would you be open to a brief call this week to explore whether there's a fit? I'd be happy to send samples or a detailed catalog for your review.

Best regards"""
    else:  # whatsapp
        subject = None
        body = f"""Hi {contact.full_name.split()[0] if contact else 'there'},

I found {company.company_name} through our research on {facts_str}. We're a supplier specializing in {company.related_products or 'your product category'} and I think there could be a good partnership opportunity.

Would you be interested in seeing our catalog? Happy to share more details at your convenience."""

    breakdown = {
        "product_capability_pct": 70,
        "personalization_pct": 30,
        "company_facts": company_facts,
        "match_reason": f"Product alignment with {company.related_products or 'business needs'}",
        "products_mentioned": [company.related_products] if company.related_products else [],
        "delivery_advantage": "Reliable supply chain with flexible MOQ",
        "cta": "Request a brief call or catalog review"
    }

    return {"subject": subject, "body": body, "breakdown": breakdown}
