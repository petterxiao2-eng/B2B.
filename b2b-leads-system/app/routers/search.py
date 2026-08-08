from datetime import datetime
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app import models, schemas
from app.services import (
    serp_search, website_scraper, ai_analysis, scoring, normalize,
    verify, directory_crawler, search_matrix, country_matrix,
)

router = APIRouter(prefix="/api/projects/{project_id}/search", tags=["search"])

# 单轮搜索的查询总量上限，避免 API 额度被瞬间打满（Google/Bing × 分页 × 查询数）
MAX_QUERIES_PER_RUN = 50

# 已知的B2B聚合/社媒平台域名
KNOWN_AGGREGATOR_DOMAINS = [
    "indiamart.com", "globalsources.com", "made-in-china.com",
    "tradekey.com", "alibaba.com", "linkedin.com", "facebook.com",
    "opencorporates.com",
]
# 其中"行业目录/聚合"类才做深抓
DIRECTORY_CRAWL_DOMAINS = {
    "indiamart.com", "globalsources.com", "made-in-china.com",
    "tradekey.com", "alibaba.com", "opencorporates.com",
}

SOCIAL_DOMAINS = {"linkedin.com", "facebook.com"}

# 规范化"发现渠道"（需求第二轮固定取值）
DISCOVERY_CHANNELS = {"google_serp", "linkedin_public", "facebook_public", "company_website", "trade_directory"}


def _discovery_channel(source_type: str) -> str:
    """把内部 source_type 归一到 5 个固定发现渠道之一。"""
    st = (source_type or "").lower()
    if st in ("linkedin", "linkedin_public"):
        return "linkedin_public"
    if st in ("facebook", "facebook_public"):
        return "facebook_public"
    if st == "trade_directory":
        return "trade_directory"
    if st == "company_website":
        return "company_website"
    # google_serp / bing_serp / 其他 → 统一归到搜索结果页
    return "google_serp"


def _is_aggregator(domain: str) -> bool:
    return any(agg in domain for agg in KNOWN_AGGREGATOR_DOMAINS)


def _is_directory_crawl(domain: str) -> bool:
    return any(agg in domain for agg in DIRECTORY_CRAWL_DOMAINS)


def _is_social(domain: str) -> bool:
    return any(s in domain for s in SOCIAL_DOMAINS)


def _looks_like_url(url: str) -> bool:
    from urllib.parse import urlparse
    try:
        p = urlparse(url)
        return p.scheme in ("http", "https") and bool(p.netloc)
    except Exception:
        return False


@router.post("/trigger", response_model=schemas.SearchTaskOut)
def trigger_search(
    project_id: int,
    payload: schemas.SearchTaskTrigger,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    project = db.query(models.Project).get(project_id)
    if not project:
        raise HTTPException(404, "项目不存在")

    if payload.keyword_set_id:
        keyword_sets = [db.query(models.KeywordSet).get(payload.keyword_set_id)]
    else:
        keyword_sets = db.query(models.KeywordSet).filter_by(project_id=project_id, is_active=True).all()

    if not keyword_sets or not keyword_sets[0]:
        raise HTTPException(400, "该项目还没有配置关键词矩阵")

    task = models.SearchTask(
        project_id=project_id,
        keyword_set_id=keyword_sets[0].id if len(keyword_sets) == 1 else None,
        status=models.TaskStatus.PENDING,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    background_tasks.add_task(_run_search_pipeline, task.id, [ks.id for ks in keyword_sets], payload.max_results_per_query)

    return task


@router.get("", response_model=list[schemas.SearchTaskOut])
def list_search_tasks(project_id: int, db: Session = Depends(get_db)):
    return db.query(models.SearchTask).filter_by(project_id=project_id).order_by(models.SearchTask.created_at.desc()).all()


def _dedup_exists(db, project_id, dedup_key):
    return db.query(models.Company).filter_by(project_id=project_id, dedup_key=dedup_key).first()


def _record_source(db, company, gq: search_matrix.GeneratedQuery, source_url: str, source_type: str, snippet: str = "", discovered_from: str = ""):
    """把一条把公司带入系统的来源写入 company_sources（可追溯）。"""
    db.add(models.CompanySource(
        company_id=company.id,
        source_type=source_type,
        source_discovered_from=discovered_from or _discovery_channel(source_type),
        source_url=source_url,
        source_keyword=gq.query,
        source_country=gq.country_code or "",
        original_keyword=gq.original_keyword,
        translated_keyword=gq.translated_keyword,
        language=gq.language,
        crawl_time=datetime.utcnow(),
        snippet=snippet,
    ))


def _ingest_website_company(
    db, project, website, company_name, source_url, source_type,
    region_code, gq, weights, thresholds, task,
) -> tuple[bool, bool]:
    """对一家有官网的公司：去重 → 官网抓取 → 真实性验证 → AI背调 → 评分 → 来源追溯 → 落库。
    返回 (是否新建公司, 是否通过真实性验证)。
    """
    domain = normalize.extract_domain(website)
    if not domain:
        return False, False
    discovered_from = _discovery_channel(source_type)
    dedup_key = domain
    existing = _dedup_exists(db, project.id, dedup_key)
    if existing:
        _record_source(db, existing, gq, source_url, source_type, "", discovered_from=discovered_from)
        db.commit()
        return False, False

    company = models.Company(
        project_id=project.id,
        website=website,
        website_domain=domain,
        dedup_key=dedup_key,
        source_url=source_url,
        source_platform=source_type,
        source_type=source_type,
        source_discovered_from=discovered_from,
        source_keyword=gq.query,
        original_keyword=gq.original_keyword,
        translated_keyword=gq.translated_keyword,
        language=gq.language,
        region_code=region_code,
        company_name=(company_name or domain)[:300],
        verified_status="背调进行中",
    )
    db.add(company)
    db.flush()  # 取 company.id 供验证/评分/来源子表使用

    # 1) 官网真实抓取（含逐页来源、邮箱/电话/WhatsApp/LinkedIn/Facebook）
    scrape_result = {}
    try:
        scrape_result = website_scraper.scrape_company_website(website)
    except Exception as e:
        scrape_result = {"reachable": False, "error": str(e)}

    company.crawl_time = datetime.utcnow()
    company.original_pages = scrape_result.get("pages_scraped", [])

    # 2) 真实性验证（DNS / HTTP / SSL / MX）—— 写入 company_verifications 历史 + Company 缓存
    verify_result = verify.verify_company_website(website)
    company.dns_valid = verify_result["dns_valid"]
    company.http_status = verify_result["http_status"]
    company.ssl_valid = verify_result["ssl_valid"]
    company.mx_valid = verify_result["mx_valid"]
    db.add(models.CompanyVerification(
        company_id=company.id,
        dns_valid=verify_result["dns_valid"],
        dns_records=verify_result["dns_records"],
        http_status=verify_result["http_status"],
        ssl_valid=verify_result["ssl_valid"],
        ssl_issuer=verify_result["ssl_issuer"],
        ssl_expiry=verify_result["ssl_expiry"],
        mx_valid=verify_result["mx_valid"],
        mx_records=verify_result["mx_records"],
        checked_at=verify_result["checked_at"],
    ))

    ai_report = {}
    if scrape_result.get("reachable"):
        try:
            ai_report = ai_analysis.analyze_website_scrape(scrape_result, company.company_name)
        except ai_analysis.AIAnalysisError:
            ai_report = {}

        # 联系方式逐条落库并标注来源页（可追溯，绝不 AI 猜测）
        _contact_ct = datetime.utcnow()
        for idx, e in enumerate(scrape_result.get("emails_found", []) or []):
            db.add(models.CompanyContact(company_id=company.id, contact_type="email", value=e["value"], source_page=e["source_page"], source_url=e["source_page"], source_type=source_type, crawl_time=_contact_ct, is_primary=(idx == 0)))
        for p in scrape_result.get("phones_found", []) or []:
            db.add(models.CompanyContact(company_id=company.id, contact_type="phone", value=p["value"], source_page=p["source_page"], source_url=p["source_page"], source_type=source_type, crawl_time=_contact_ct, is_primary=False))
        for w in scrape_result.get("whatsapp_found", []) or []:
            db.add(models.CompanyContact(company_id=company.id, contact_type="whatsapp", value=w["value"], source_page=w["source_page"], source_url=w["source_page"], source_type=source_type, crawl_time=_contact_ct, is_primary=False))

        social = scrape_result.get("social_links", {}) or {}
        company.linkedin = social.get("linkedin", "") or ""
        company.facebook = social.get("facebook", "") or ""
        if scrape_result.get("whatsapp_found"):
            company.whatsapp = scrape_result["whatsapp_found"][0]["value"]

    # 主联系方式（取首个邮箱/电话，并标记 primary）
    primary_email = (scrape_result.get("emails_found") or [{}])[0].get("value", "") if scrape_result.get("emails_found") else ""
    primary_phone = (scrape_result.get("phones_found") or [{}])[0].get("value", "") if scrape_result.get("phones_found") else ""
    company.email = primary_email
    company.phone = primary_phone
    company.phone_e164 = normalize.normalize_phone(primary_phone, region_code or "US") if primary_phone else ""
    if primary_email:
        company.email_valid = normalize.check_email_valid(primary_email)
        company.mx_valid = company.email_valid

    # 3) AI 背调字段
    company.business_type = ai_report.get("business_type", "")
    company.products_summary = ai_report.get("products_summary", "")
    company.company_size_estimate = ai_report.get("company_size_estimate", "")
    company.background_report = ai_report or {}

    # 4) 评分（真实加权计算）→ 写入 company_scores 历史 + Company 缓存
    score_result = scoring.compute_total_score(
        scrape_result=scrape_result,
        ai_report=ai_report,
        company_email=primary_email,
        company_phone=primary_phone,
        email_valid=company.email_valid,
        phone_e164=company.phone_e164,
        contacts=ai_report.get("possible_contacts", []) or [],
        target_keywords=[],
        weights=weights,
        grade_thresholds=thresholds,
    )
    company.score_total = score_result["total"]
    company.purchase_probability = score_result["total"]
    company.grade = score_result["grade"]
    company.score_breakdown = score_result["breakdown"]
    company.score_reason = score_result.get("reason", "")
    db.add(models.CompanyScore(
        company_id=company.id,
        total=score_result["total"],
        grade=score_result["grade"],
        breakdown=score_result["breakdown"],
        reason=score_result.get("reason", ""),
        model="weighted_v1",
        computed_at=datetime.utcnow(),
    ))

    # 5) AI 提取的决策人（仅官网公开信息，禁止 AI 生成邮箱/电话）
    for c in ai_report.get("possible_contacts", []) or []:
        db.add(models.Contact(
            company_id=company.id,
            name=c.get("name", ""),
            title=c.get("title", ""),
            source_note=c.get("source_note", "官网公开信息"),
            source_url="",
            source_type=source_type,
            crawl_time=datetime.utcnow(),
        ))

    company.verified_status = "已背调" if scrape_result.get("reachable") else "官网不可达/未查实"

    # 6) 来源追溯
    _record_source(db, company, gq, source_url, source_type, scrape_result.get("raw_text_snippets", [""])[0][:500] if scrape_result.get("raw_text_snippets") else "", discovered_from=discovered_from)

    db.commit()
    task.new_companies = (task.new_companies or 0) + 1

    # 真实性验证通过判定：DNS 可解析 / HTTP 可达 / SSL 有效 / MX 存在，任一即通过
    verified = bool(company.dns_valid) or (company.http_status == 200) or bool(company.ssl_valid) or bool(company.mx_valid)
    return True, verified


def _ingest_directory_lead(
    db, project, company_name, source_url, source_type, region_code, gq, task,
) -> tuple[bool, bool]:
    """行业目录里只给了公司名、没给官网的条目：作为可追溯线索留存。返回 (是否新建, 验证是否通过)。"""
    discovered_from = _discovery_channel(source_type)
    dedup_key = f"{source_url}::{company_name}"
    existing = _dedup_exists(db, project.id, dedup_key)
    if existing:
        _record_source(db, existing, gq, source_url, source_type, "", discovered_from=discovered_from)
        db.commit()
        return False, False
    company = models.Company(
        project_id=project.id,
        website="",
        website_domain="",
        dedup_key=dedup_key,
        source_url=source_url,
        source_platform=source_type,
        source_type=source_type,
        source_discovered_from=discovered_from,
        source_keyword=gq.query,
        original_keyword=gq.original_keyword,
        translated_keyword=gq.translated_keyword,
        language=gq.language,
        region_code=region_code,
        company_name=(company_name or "未知")[:300],
        verified_status="目录线索，待人工核实官网",
        background_report={"note": "来自行业目录公开列表页，未抓到官网，需人工补全。"},
    )
    db.add(company)
    db.flush()
    _record_source(db, company, gq, source_url, source_type, "", discovered_from=discovered_from)
    db.commit()
    task.new_companies = (task.new_companies or 0) + 1
    return True, False


def _ingest_social(
    db, project, page_url, source_url, platform, region_code, gq, task,
) -> tuple[bool, bool]:
    """LinkedIn/Facebook 公开公司页：仅保存 company page URL + source_url，不登录、不深抓。返回 (是否新建, 验证是否通过)。"""
    discovered_from = _discovery_channel(platform)
    dedup_key = page_url
    existing = _dedup_exists(db, project.id, dedup_key)
    if existing:
        _record_source(db, existing, gq, page_url, platform, "", discovered_from=discovered_from)
        db.commit()
        return False, False
    company = models.Company(
        project_id=project.id,
        website=page_url,  # company page URL
        website_domain=normalize.extract_domain(page_url),
        dedup_key=dedup_key,
        source_url=page_url,  # 来源（发现该公开页的 SERP 结果）
        source_platform=platform,
        source_type=platform,
        source_discovered_from=discovered_from,
        source_keyword=gq.query,
        original_keyword=gq.original_keyword,
        translated_keyword=gq.translated_keyword,
        language=gq.language,
        region_code=region_code,
        company_name=(gq.product_keyword or platform)[:300],
        verified_status="LinkedIn/Facebook 公开页，待人工核实",
        background_report={"note": f"来自{platform}公开公司页，按合规边界仅保存 URL，未抓取登录内容。"},
    )
    db.add(company)
    db.flush()
    _record_source(db, company, gq, page_url, platform, "", discovered_from=discovered_from)
    db.commit()
    task.new_companies = (task.new_companies or 0) + 1
    return True, False


def _run_search_pipeline(task_id: int, keyword_set_ids: list[int], max_results: int):
    """
    后台任务主流程（V2 真实化改造）。

    数据链路（全真实）：
    搜索矩阵(行业+产品+国家+客户类型) → 国家矩阵(语言/domain) → 多 Provider 真实搜索(Google+Bing)
    → 来源判定：
        - 官网 → website_scraper 真实抓取 + verify 真实性验证 + AI 背调 + 评分
        - 行业目录 → directory_crawler 真实提取公司（带回填官网）
        - LinkedIn/Facebook 公开页 → 仅保存 company page URL + source_url（合规，不深抓）
    每条来源写入 company_sources（source_keyword/original/translated/language 可追溯）。
    验证结果写入 company_verifications，评分写入 company_scores。
    计数：search_hits = 原始搜索命中数（含重复/聚合，参考）；real_companies = 真实新增公司数（与前端/导出一致）。
    """
    db = SessionLocal()
    try:
        task = db.query(models.SearchTask).get(task_id)
        task.status = models.TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        db.commit()

        project = db.query(models.SearchTask).get(task.project_id).project
        template = db.query(models.ScoringTemplate).filter_by(project_id=project.id).first()
        weights = template.weights if template else None
        thresholds = template.grade_thresholds if template else None

        total_search_hits = 0
        funnel_queries = 0   # 阶段1：生成查询数
        funnel_serp = 0      # 阶段2：SERP 返回数
        funnel_dedup = 0     # 阶段3：去重后候选数
        funnel_verified = 0  # 阶段4：验证通过数

        for ks_id in keyword_set_ids:
            ks = db.query(models.KeywordSet).get(ks_id)
            if not ks or not ks.is_active:
                continue

            country = country_matrix.get_country(ks.region_code or ks.country_profile)
            country_code = country.code

            # AI 本地化翻译缓存（每个产品词只翻译一次）
            _trans_cache: dict[str, str] = {}

            def _translator(kw: str, lang: str) -> str:
                if kw not in _trans_cache:
                    _trans_cache[kw] = ai_analysis.localize_keyword(kw, lang)
                return _trans_cache[kw]

            # 默认英文搜索；非英语国家额外开启深度本地化（当地语言关键词）
            target_lang = country.lang
            translator_arg = _translator if target_lang != "en" else None

            product_queries = search_matrix.generate_queries(
                product_keywords=ks.product_keywords,
                country_name=country.name,
                tiers=ks.customer_type_tiers or None,
                industry_keywords=ks.industry_keywords,
                translator=translator_arg,
                target_lang=target_lang,
            )
            social_queries = search_matrix.generate_social_queries(
                product_keywords=ks.product_keywords,
                country_name=country.name,
                country_code=country_code,
            )
            all_queries = (product_queries + social_queries)[:MAX_QUERIES_PER_RUN]

            try:
                manager = serp_search.SearchManager()
            except serp_search.SerpSearchError as e:
                task.error_message += f"[Provider] {str(e)}\n"
                continue

            try:
                candidates, raw_hits = manager.search_queries(
                    all_queries, country, num=min(max_results, 10), pages=2
                )
            except serp_search.SerpSearchError as e:
                task.error_message += f"[搜索] {str(e)}\n"
                continue

            total_search_hits += raw_hits
            funnel_queries += len(all_queries)
            funnel_serp += raw_hits
            funnel_dedup += len(candidates)

            for cand in candidates:
                gq: search_matrix.GeneratedQuery = cand["query_obj"]
                gq.country_code = country_code
                link = cand["link"]
                if not link:
                    continue
                domain = normalize.extract_domain(link)
                if not domain:
                    continue

                source_type = gq.source_type_override or "google_serp"
                platform = gq.source_type_override  # linkedin / facebook

                # 社交公开页（含 override 与普通查询命中社媒）：仅保存 URL
                if platform in ("linkedin", "facebook") or _is_social(domain):
                    _ingest_social(db, project, link, link, platform or "social", region_code=country_code, gq=gq, task=task)
                    continue

                if _is_aggregator(domain) and _is_directory_crawl(domain):
                    # 行业目录：真实抓取列表页，提取公司
                    try:
                        extracted = directory_crawler.extract_companies(link)
                    except Exception as e:
                        task.error_message += f"[目录抓取 {link}] {str(e)}\n"
                        extracted = []
                    for ec in extracted:
                        if ec.get("website"):
                            created, verified = _ingest_website_company(
                                db, project, ec["website"], ec["company_name"],
                                source_url=link, source_type="trade_directory",
                                region_code=country_code, gq=gq, weights=weights,
                                thresholds=thresholds, task=task,
                            )
                            if created and verified:
                                funnel_verified += 1
                        else:
                            _ingest_directory_lead(
                                db, project, ec["company_name"], link,
                                "trade_directory", country_code, gq, task,
                            )
                else:
                    # 自建官网：完整背调
                    created, verified = _ingest_website_company(
                        db, project, link, cand["title"],
                        source_url=link, source_type=source_type,
                        region_code=country_code, gq=gq, weights=weights,
                        thresholds=thresholds, task=task,
                    )
                    if created and verified:
                        funnel_verified += 1

        # 统一计数口径 + Search Funnel 漏斗统计
        task.search_hits = total_search_hits
        task.results_found = total_search_hits  # 兼容旧字段（原始命中参考值）
        task.queries_generated = funnel_queries
        task.serp_results = funnel_serp
        task.dedup_count = funnel_dedup
        task.verified_count = funnel_verified
        task.real_companies = task.new_companies or 0
        task.query_used = ""  # 查询已由 company_sources 逐条记录，不再堆成一串
        task.status = models.TaskStatus.SUCCESS
        task.finished_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        task = db.query(models.SearchTask).get(task_id)
        task.status = models.TaskStatus.FAILED
        task.error_message = (task.error_message or "") + str(e)
        task.finished_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()


# ---------- 独立爬虫入口：Company Website / Trade Directory ----------
# 这两项功能原先已内嵌在统一搜索流程里（trade_directory 经 directory_crawler 真实抓取、
# company_website 经 website_scraper 真实抓取），现额外暴露为可单独触发、真实产数的按钮。

def _project_weights_thresholds(db, project) -> tuple:
    template = db.query(models.ScoringTemplate).filter_by(project_id=project.id).first()
    return (template.weights if template else None, template.grade_thresholds if template else None)


def _direct_gq(region_code: str, source_type_override: str) -> search_matrix.GeneratedQuery:
    """为'直接给 URL 抓取'构造最小 GeneratedQuery（无搜索关键词）。"""
    return search_matrix.GeneratedQuery(
        query="", product_keyword="", customer_type="", country_name="",
        country_code=region_code, original_keyword="", translated_keyword="",
        language="", source_type_override=source_type_override,
    )


def _run_crawl_website(task_id: int, url: str, region_code: str):
    """直接抓取一个公司官网：真实抓取 + 验证 + 背调 + 评分，落库（source_discovered_from=company_website）。"""
    db = SessionLocal()
    try:
        task = db.query(models.SearchTask).get(task_id)
        task.status = models.TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        db.commit()
        project = task.project
        weights, thresholds = _project_weights_thresholds(db, project)
        gq = _direct_gq(region_code, "company_website")
        created, verified = _ingest_website_company(
            db, project, url, normalize.extract_domain(url) or url,
            source_url=url, source_type="company_website",
            region_code=region_code, gq=gq, weights=weights, thresholds=thresholds, task=task,
        )
        task.queries_generated = 0
        task.serp_results = 0
        task.dedup_count = 1
        task.verified_count = 1 if (created and verified) else 0
        task.search_hits = 0
        task.results_found = 0
        task.real_companies = task.new_companies or 0
        task.status = models.TaskStatus.SUCCESS
        task.finished_at = datetime.utcnow()
        db.commit()
    except Exception as e:
        task = db.query(models.SearchTask).get(task_id)
        task.status = models.TaskStatus.FAILED
        task.error_message = (task.error_message or "") + str(e)
        task.finished_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()


def _run_crawl_directory(task_id: int, url: str, region_code: str):
    """直接抓取一个行业目录列表页：真实提取公司，逐条入库（source_discovered_from=trade_directory）。"""
    db = SessionLocal()
    try:
        task = db.query(models.SearchTask).get(task_id)
        task.status = models.TaskStatus.RUNNING
        task.started_at = datetime.utcnow()
        db.commit()
        project = task.project
        weights, thresholds = _project_weights_thresholds(db, project)
        gq = _direct_gq(region_code, "trade_directory")

        try:
            extracted = directory_crawler.extract_companies(url)
        except Exception as e:
            task.error_message += f"[目录抓取 {url}] {str(e)}\n"
            extracted = []

        verified_n = 0
        for ec in extracted:
            if ec.get("website"):
                created, verified = _ingest_website_company(
                    db, project, ec["website"], ec["company_name"],
                    source_url=url, source_type="trade_directory",
                    region_code=region_code, gq=gq, weights=weights, thresholds=thresholds, task=task,
                )
                if created and verified:
                    verified_n += 1
            else:
                _ingest_directory_lead(db, project, ec["company_name"], url, "trade_directory", region_code, gq, task)

        task.queries_generated = 0
        task.serp_results = 0
        task.dedup_count = len(extracted)
        task.verified_count = verified_n
        task.search_hits = 0
        task.results_found = 0
        task.real_companies = task.new_companies or 0
        task.status = models.TaskStatus.SUCCESS
        task.finished_at = datetime.utcnow()
        db.commit()
    except Exception as e:
        task = db.query(models.SearchTask).get(task_id)
        task.status = models.TaskStatus.FAILED
        task.error_message = (task.error_message or "") + str(e)
        task.finished_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()


@router.post("/crawl-website", response_model=schemas.SearchTaskOut)
def crawl_company_website(
    project_id: int,
    payload: schemas.CrawlUrlPayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """手动输入一个公司官网 URL，真实抓取并入库（不经由搜索引擎）。"""
    project = db.query(models.Project).get(project_id)
    if not project:
        raise HTTPException(404, "项目不存在")
    if not _looks_like_url(payload.url):
        raise HTTPException(400, "请提供合法的 http(s) 官网 URL")
    region_code = payload.region_code or (project.target_regions[0] if project.target_regions else "US")
    task = models.SearchTask(project_id=project_id, task_type="website", status=models.TaskStatus.PENDING)
    db.add(task)
    db.commit()
    db.refresh(task)
    background_tasks.add_task(_run_crawl_website, task.id, payload.url, region_code)
    return task


@router.post("/crawl-directory", response_model=schemas.SearchTaskOut)
def crawl_trade_directory(
    project_id: int,
    payload: schemas.CrawlUrlPayload,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """手动输入一个行业目录/列表页 URL，真实提取公司并入库。"""
    project = db.query(models.Project).get(project_id)
    if not project:
        raise HTTPException(404, "项目不存在")
    if not _looks_like_url(payload.url):
        raise HTTPException(400, "请提供合法的 http(s) 目录列表页 URL")
    region_code = payload.region_code or (project.target_regions[0] if project.target_regions else "US")
    task = models.SearchTask(project_id=project_id, task_type="directory", status=models.TaskStatus.PENDING)
    db.add(task)
    db.commit()
    db.refresh(task)
    background_tasks.add_task(_run_crawl_directory, task.id, payload.url, region_code)
    return task
