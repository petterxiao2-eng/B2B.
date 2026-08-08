from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.services import ai_analysis

router = APIRouter(prefix="/api/companies/{company_id}/outreach", tags=["outreach"])


@router.post("/generate", response_model=schemas.OutreachDraftOut)
def generate_draft(company_id: int, payload: schemas.OutreachDraftGenerate, db: Session = Depends(get_db)):
    company = db.query(models.Company).get(company_id)
    if not company:
        raise HTTPException(404, "客户不存在")

    company_dict = {
        "company_name": company.company_name,
        "products_summary": company.products_summary,
        "business_type": company.business_type,
        "background_report": company.background_report or {},
        "score_reason": company.score_reason,
    }

    try:
        result = ai_analysis.generate_outreach_draft(company_dict, channel=payload.channel, tone=payload.tone)
    except ai_analysis.AIAnalysisError as e:
        raise HTTPException(500, str(e))

    draft = models.OutreachDraft(
        company_id=company_id,
        channel=payload.channel,
        subject=result.get("subject", ""),
        body=result.get("body", ""),
        status="draft",
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


@router.get("", response_model=list[schemas.OutreachDraftOut])
def list_drafts(company_id: int, db: Session = Depends(get_db)):
    return db.query(models.OutreachDraft).filter_by(company_id=company_id).order_by(models.OutreachDraft.created_at.desc()).all()


@router.put("/{draft_id}/status")
def update_draft_status(company_id: int, draft_id: int, status: str, db: Session = Depends(get_db)):
    """状态流转: draft -> approved -> sent，或 -> rejected。
    注意：本系统只负责生成草稿并记录状态，不做自动群发；approved/sent 需要业务员在邮箱/WhatsApp客户端手动实际发送后再回来标记。"""
    if status not in ("draft", "approved", "sent", "rejected"):
        raise HTTPException(400, "非法状态")
    draft = db.query(models.OutreachDraft).filter_by(id=draft_id, company_id=company_id).first()
    if not draft:
        raise HTTPException(404, "草稿不存在")
    draft.status = status
    db.commit()
    return {"ok": True}
