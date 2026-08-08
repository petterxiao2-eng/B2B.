from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/api/projects/{project_id}/keywords", tags=["keywords"])


@router.post("", response_model=schemas.KeywordSetOut)
def create_keyword_set(project_id: int, payload: schemas.KeywordSetCreate, db: Session = Depends(get_db)):
    project = db.query(models.Project).get(project_id)
    if not project:
        raise HTTPException(404, "项目不存在")

    ks = models.KeywordSet(
        project_id=project_id,
        region_code=payload.region_code,
        product_keywords=payload.product_keywords,
        dork_filters=payload.dork_filters,
        language=payload.language,
        industry_keywords=payload.industry_keywords,
        customer_type_tiers=payload.customer_type_tiers,
        # country_profile 与 region_code 保持一致即可，pipeline 据此在 country_matrix 中查表
        country_profile=payload.country_profile or payload.region_code,
    )
    db.add(ks)
    db.commit()
    db.refresh(ks)
    return ks


@router.get("", response_model=list[schemas.KeywordSetOut])
def list_keyword_sets(project_id: int, db: Session = Depends(get_db)):
    return db.query(models.KeywordSet).filter_by(project_id=project_id).all()


@router.delete("/{keyword_set_id}")
def delete_keyword_set(project_id: int, keyword_set_id: int, db: Session = Depends(get_db)):
    ks = db.query(models.KeywordSet).filter_by(id=keyword_set_id, project_id=project_id).first()
    if not ks:
        raise HTTPException(404, "关键词集不存在")
    db.delete(ks)
    db.commit()
    return {"ok": True}


# 预置的常用 Google Dorks 模板，前端可以展示给用户直接勾选，
# 全部限定在公开可索引的页面范围内（不涉及登录墙/需授权内容）
SUGGESTED_DORKS = {
    "b2b_platforms": [
        'site:indiamart.com',
        'site:globalsources.com',
        'site:made-in-china.com',
        'site:tradekey.com',
        'site:alibaba.com "buyer"',
    ],
    "exhibitor_lists": [
        'intitle:"exhibitor list" filetype:pdf',
        'intitle:"exhibitor directory"',
    ],
    "public_association_directories": [
        'intitle:"member directory" importer',
        'site:opencorporates.com',
    ],
    "buyer_signals": [
        '"we are looking for suppliers"',
        '"request for quotation" importer',
        'intitle:"buyer" intitle:"wholesale"',
    ],
}


@router.get("/suggested-dorks")
def get_suggested_dorks(project_id: int):
    # project_id 未在此函数内使用，仅用于匹配路由前缀（FastAPI要求路径参数必须出现在函数签名里）
    return SUGGESTED_DORKS
