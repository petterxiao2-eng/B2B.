import io
from datetime import datetime

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app import models

router = APIRouter(prefix="/api/projects/{project_id}/export", tags=["export"])

EXPORT_COLUMNS = [
    "公司名称", "地区", "官网", "来源链接", "来源页面", "来源类型", "来源关键词", "搜索语言",
    "邮箱", "邮箱有效性", "电话", "电话(E.164)", "WhatsApp", "LinkedIn", "Facebook",
    "采购可能性", "评分", "等级",
    "DNS", "HTTP", "SSL", "MX",
    "核实状态", "抓取时间", "最后验证时间",
]


def _verif(v) -> str:
    if v is True:
        return "通过"
    if v is False:
        return "未通过"
    return "未知"


def _lookup_maps(db, companies: list[models.Company]) -> tuple[dict, dict]:
    """预取：每家公司的最新验证时间、首个来源页面（避免 N+1 懒加载）。"""
    ids = [c.id for c in companies]
    verified_at: dict[int, str] = {}
    if ids:
        for cid, checked_at in db.query(
            models.CompanyVerification.company_id, models.CompanyVerification.checked_at
        ).filter(models.CompanyVerification.company_id.in_(ids)).all():
            key = checked_at.strftime("%Y-%m-%d %H:%M") if checked_at else ""
            # 取最新（checked_at 越大越新）；这里用 max 比较
            if cid not in verified_at or (checked_at and (not verified_at[cid] or key > verified_at[cid])):
                verified_at[cid] = key
    source_page: dict[int, str] = {}
    if ids:
        for cid, surl in db.query(
            models.CompanySource.company_id, models.CompanySource.source_url
        ).filter(models.CompanySource.company_id.in_(ids)).all():
            if cid not in source_page and surl:
                source_page[cid] = surl
    return verified_at, source_page


def _build_dataframe(companies: list[models.Company], verified_at: dict, source_page: dict) -> pd.DataFrame:
    rows = []
    for c in companies:
        grade_val = c.grade.value if hasattr(c.grade, "value") else c.grade
        rows.append({
            "公司名称": c.company_name,
            "地区": c.region_code,
            "官网": c.website,
            "来源链接": c.source_url,
            "来源页面": source_page.get(c.id) or c.source_url,
            "来源类型": c.source_type or c.source_platform,
            "来源关键词": c.source_keyword,
            "搜索语言": c.language,
            "邮箱": c.email,
            "邮箱有效性": _verif(c.email_valid),
            "电话": c.phone,
            "电话(E.164)": c.phone_e164,
            "WhatsApp": c.whatsapp,
            "LinkedIn": c.linkedin,
            "Facebook": c.facebook,
            "采购可能性": c.purchase_probability,
            "评分": c.score_total,
            "等级": grade_val,
            "DNS": _verif(c.dns_valid),
            "HTTP": c.http_status if c.http_status is not None else "未知",
            "SSL": _verif(c.ssl_valid),
            "MX": _verif(c.mx_valid),
            "核实状态": c.verified_status,
            "抓取时间": c.crawl_time.strftime("%Y-%m-%d %H:%M") if c.crawl_time else "",
            "最后验证时间": verified_at.get(c.id, ""),
        })
    return pd.DataFrame(rows, columns=EXPORT_COLUMNS)


@router.get("/excel")
def export_excel(
    project_id: int,
    grade: str | None = Query(None),
    min_score: float | None = Query(None),
    db: Session = Depends(get_db),
):
    project = db.query(models.Project).get(project_id)
    if not project:
        raise HTTPException(404, "项目不存在")

    q = db.query(models.Company).filter_by(project_id=project_id, is_duplicate=False)
    if grade:
        q = q.filter(models.Company.grade == grade)
    if min_score is not None:
        q = q.filter(models.Company.score_total >= min_score)
    companies = q.order_by(models.Company.score_total.desc()).all()

    verified_at, source_page = _lookup_maps(db, companies)
    df = _build_dataframe(companies, verified_at, source_page)
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="客户清单")
    buffer.seek(0)

    filename = f"{project.name}_客户清单_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/csv")
def export_csv(
    project_id: int,
    grade: str | None = Query(None),
    min_score: float | None = Query(None),
    db: Session = Depends(get_db),
):
    project = db.query(models.Project).get(project_id)
    if not project:
        raise HTTPException(404, "项目不存在")

    q = db.query(models.Company).filter_by(project_id=project_id, is_duplicate=False)
    if grade:
        q = q.filter(models.Company.grade == grade)
    if min_score is not None:
        q = q.filter(models.Company.score_total >= min_score)
    companies = q.order_by(models.Company.score_total.desc()).all()

    verified_at, source_page = _lookup_maps(db, companies)
    df = _build_dataframe(companies, verified_at, source_page)
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)

    filename = f"{project.name}_客户清单_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
