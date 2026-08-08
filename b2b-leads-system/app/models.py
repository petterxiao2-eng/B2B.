"""
核心数据模型。

设计说明：
- Project：一个业务赛道/产品线的独立项目，拥有自己的关键词矩阵和评分模板
- KeywordSet：项目下的关键词矩阵配置（产品词 + 国家/地区 + 平台限定）
- SearchTask：定时/手动触发的一次搜索任务，记录执行状态
- Company：背调后的公司档案（核心实体）
- Contact：公司下的联系人（决策人/采购负责人等，仅来自公开渠道）
- ScoreLog：评分历史，记录每次评分依据，便于审计和调整评分模型
- OutreachDraft：AI 生成的沟通草稿（邮件/WhatsApp文案），人工确认后才发出
"""
import enum
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Text, Float, Boolean, DateTime,
    ForeignKey, JSON, Enum as SAEnum, UniqueConstraint
)
from sqlalchemy.orm import relationship

from app.database import Base


class GradeEnum(str, enum.Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    UNSCORED = "unscored"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class Project(Base):
    """独立项目：一个业务赛道，例如'LED灯具-中东市场'"""
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, default="")
    # 目标国家/地区列表，例如 ["SA", "AE", "UZ", "KE", "NG", "PH", "VN"]
    target_regions = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    keyword_sets = relationship("KeywordSet", back_populates="project", cascade="all, delete-orphan")
    companies = relationship("Company", back_populates="project", cascade="all, delete-orphan")
    scoring_template = relationship("ScoringTemplate", back_populates="project", uselist=False, cascade="all, delete-orphan")
    search_tasks = relationship("SearchTask", back_populates="project", cascade="all, delete-orphan")


class KeywordSet(Base):
    """项目下的关键词矩阵配置，支持按国家配置不同的本地化关键词"""
    __tablename__ = "keyword_sets"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    region_code = Column(String(10), nullable=False)  # ISO国家代码，如 SA / AE / UZ
    # 产品关键词列表，例如 ["led floodlight", "led street light importer"]
    product_keywords = Column(JSON, default=list)
    # Google Dorks 限定词，例如 site:indiamart.com / intitle:"buyer" 等
    dork_filters = Column(JSON, default=list)
    # 行业关键词列表，例如 ["solar energy", "photovoltaics"]
    industry_keywords = Column(JSON, default=list)
    # 启用的客户类型分层：["Tier1","Tier2","Tier3"]；空列表=全部启用
    customer_type_tiers = Column(JSON, default=list)
    # 关联国家矩阵的国家代码（默认同 region_code）
    country_profile = Column(String(10), default="")
    language = Column(String(10), default="en")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="keyword_sets")


class ScoringTemplate(Base):
    """项目独立的评分模板，权重可配置"""
    __tablename__ = "scoring_templates"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), unique=True, nullable=False)
    # 各维度权重（0-100，总和建议=100），示例见 services/scoring.py 的 DEFAULT_WEIGHTS
    weights = Column(JSON, default=dict)
    # 分级阈值，例如 {"A": 80, "B": 60, "C": 40, "D": 0}
    grade_thresholds = Column(JSON, default=dict)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="scoring_template")


class SearchTask(Base):
    """一次搜索任务的执行记录"""
    __tablename__ = "search_tasks"

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    keyword_set_id = Column(Integer, ForeignKey("keyword_sets.id"), nullable=True)
    status = Column(SAEnum(TaskStatus), default=TaskStatus.PENDING)
    task_type = Column(String(20), default="search")  # search / website / directory（任务来源类型，供日志区分）
    query_used = Column(Text, default="")
    results_found = Column(Integer, default=0)
    new_companies = Column(Integer, default=0)
    search_hits = Column(Integer, default=0)  # 原始搜索命中数（含重复/聚合，参考值）
    real_companies = Column(Integer, default=0)  # 去重后真实新增公司数（与前端/导出一致）

    # === Search Funnel 漏斗统计（需求第二轮）===
    queries_generated = Column(Integer, default=0)  # 阶段1：生成的查询数量
    serp_results = Column(Integer, default=0)       # 阶段2：SERP 返回数量（各 Provider/页 organic_results 总和）
    dedup_count = Column(Integer, default=0)        # 阶段3：去重后候选数量（跨 Provider 按 link 去重）
    verified_count = Column(Integer, default=0)     # 阶段4：验证通过的真实公司数量
    # real_companies 即阶段5：最终客户数量（漏斗终点）

    error_message = Column(Text, default="")
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="search_tasks")


class Company(Base):
    """公司档案 —— 核心数据实体

    数据库重新设计（V2 审计后）：
    - 补齐需求字段：whatsapp / linkedin / facebook / purchase_probability
    - 补齐真实性验证字段：dns_valid / http_status / ssl_valid / mx_valid
    - 补齐追溯字段：crawl_time / original_pages（抓取过的页面列表）
    - 联系方式逐条可追溯见 CompanyContact 表
    """
    __tablename__ = "companies"
    __table_args__ = (
        UniqueConstraint("project_id", "dedup_key", name="uq_project_dedup_key"),
    )

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    # === 用户要求的核心字段 ===
    company_name = Column(String(300), default="")
    address = Column(Text, default="")
    email = Column(String(200), default="")  # 主邮箱（来自 company_contacts 里 is_primary 的那条）
    email_valid = Column(Boolean, nullable=True)  # 基础格式/域名MX校验结果（兼容旧逻辑）
    website = Column(String(500), default="")
    website_domain = Column(String(300), default="")  # 官网域名，仅供展示/筛选用
    dedup_key = Column(String(500), nullable=True, default=None)  # 实际去重依据：自建官网=域名；聚合平台线索=完整来源链接；留空=不参与去重(如手动录入无官网的线索)
    phone = Column(String(50), default="")  # 主电话
    phone_e164 = Column(String(30), default="")  # 标准化后的号码
    source_url = Column(Text, default="")  # 首次发现来源链接（搜索结果页 / 目录列表页）
    source_platform = Column(String(100), default="")  # google / trade_directory / linkedin / facebook / manual 等
    source_type = Column(String(50), default="")  # 规范化来源类型：google_serp/bing_serp/linkedin/facebook/trade_directory/company_website/manual
    source_discovered_from = Column(String(50), default="")  # 规范化发现渠道（需求第二轮）：google_serp/linkedin_public/facebook_public/company_website/trade_directory
    source_keyword = Column(String(500), default="")  # 命中该公司的具体搜索关键词/查询
    original_keyword = Column(String(500), default="")  # AI 本地化前的原始关键词
    translated_keyword = Column(String(500), default="")  # AI 本地化后的当地语言关键词
    language = Column(String(10), default="")  # 该来源使用的搜索语言（en/de/tr...）

    region_code = Column(String(10), default="")
    business_type = Column(String(100), default="")  # 零售商/批发商/OEM代工厂 等
    products_summary = Column(Text, default="")  # AI提取的经营品类摘要
    company_size_estimate = Column(String(100), default="")

    # === 需求补齐字段（V2）===
    whatsapp = Column(String(50), default="")       # WhatsApp 号码（来自官网公开 wa.me / whatsapp.com 链接）
    linkedin = Column(String(500), default="")      # LinkedIn 公司主页（来自官网公开链接）
    facebook = Column(String(500), default="")      # Facebook 公共主页（来自官网公开链接）
    purchase_probability = Column(Float, default=0.0)  # 采购可能性评分（0-100，由评分引擎推导）

    # === 真实性验证字段（V2，落库可追溯）===
    dns_valid = Column(Boolean, nullable=True)   # 域名 DNS 是否可解析
    http_status = Column(Integer, nullable=True)  # 官网 HTTP 状态码（200=可达）
    ssl_valid = Column(Boolean, nullable=True)   # SSL 证书是否有效
    mx_valid = Column(Boolean, nullable=True)    # 邮箱域名 MX 记录是否存在

    # === 追溯字段（V2）===
    crawl_time = Column(DateTime, nullable=True)   # 最近一次背调抓取时间
    original_pages = Column(JSON, default=list)    # 实际抓取过的页面 URL 列表（首页/About/Contact…）

    # === 评分 ===
    score_total = Column(Float, default=0.0)
    grade = Column(SAEnum(GradeEnum), default=GradeEnum.UNSCORED)
    score_breakdown = Column(JSON, default=dict)  # 各维度得分明细
    score_reason = Column(Text, default="")  # AI生成的评分理由

    # === 背调报告（对应用户的《客户背调》模板结构）===
    background_report = Column(JSON, default=dict)  # 完整背调报告 JSON，前端渲染成卡片

    # === 状态 ===
    is_duplicate = Column(Boolean, default=False)
    duplicate_of_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    verified_status = Column(String(50), default="未通过公开渠道查实")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="companies")
    contacts = relationship("Contact", back_populates="company", cascade="all, delete-orphan")
    company_contacts = relationship("CompanyContact", back_populates="company", cascade="all, delete-orphan")
    company_sources = relationship("CompanySource", back_populates="company", cascade="all, delete-orphan")
    verifications = relationship("CompanyVerification", back_populates="company", cascade="all, delete-orphan")
    scores = relationship("CompanyScore", back_populates="company", cascade="all, delete-orphan")
    outreach_drafts = relationship("OutreachDraft", back_populates="company", cascade="all, delete-orphan")


class Contact(Base):
    """
    公司联系人 —— 仅收录来自公开渠道（公司官网 About/Contact 页、
    公开新闻稿、公开展会名录）的姓名与职位，不做社媒批量抓取。
    """
    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    name = Column(String(200), default="")
    title = Column(String(200), default="")  # 职位，如 Purchasing Manager
    email = Column(String(200), default="")
    phone = Column(String(50), default="")
    source_note = Column(String(300), default="")  # 信息来源说明，例如 "公司官网About页"
    source_url = Column(Text, default="")  # 该联系人信息提取自哪个具体页面（可追溯）
    source_type = Column(String(50), default="")  # 发现渠道（与所属公司一致）
    crawl_time = Column(DateTime, nullable=True)  # 发现/抓取时间
    is_decision_maker = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="contacts")


class CompanyContact(Base):
    """公司公开联系方式明细 —— 每条邮箱/电话/WhatsApp 都记录其原始来源页，确保可点击验证。

    与 Contact（决策人）区分：本表只承载'从官网/目录页公开抓取到的联系方式'，
    每条都带 source_page，满足'企业联系方式必须可追溯'的硬要求。
    """
    __tablename__ = "company_contacts"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    contact_type = Column(String(20), default="email")  # email / phone / whatsapp
    value = Column(String(300), default="")  # 具体邮箱/电话号码
    source_page = Column(Text, default="")  # 该联系方式被发现的具体页面 URL（点击即可验证）
    source_url = Column(Text, default="")  # 该联系方式被发现的具体页面 URL（与 source_page 同源，便于单字段检索/导出）
    source_type = Column(String(50), default="")  # 该联系方式的发现渠道（与所属公司一致：google_serp/company_website/trade_directory...）
    crawl_time = Column(DateTime, nullable=True)  # 该联系方式被发现/抓取的时间
    is_primary = Column(Boolean, default=False)  # 是否作为公司主联系方式

    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="company_contacts")


class CompanySource(Base):
    """公司来源追溯 —— 每一条把公司带入系统的来源都独立记录，确保可审计。

    对应需求『每条企业数据必须保存 source_url / source_type / source_keyword /
    source_country / crawl_time』，并扩展 AI 本地化关键词（original/translated/language）。
    一家公司可有多个来源（例如同时被 Google 与 Bing 命中、或被目录与官网共同佐证）。
    """
    __tablename__ = "company_sources"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    source_type = Column(String(50), default="")  # google_serp / bing_serp / linkedin / facebook / trade_directory / company_website / manual
    source_discovered_from = Column(String(50), default="")  # 规范化发现渠道：google_serp/linkedin_public/facebook_public/company_website/trade_directory
    source_url = Column(Text, default="")  # 发现该线索的原始 SERP 结果页 / 目录列表页 URL
    source_keyword = Column(String(500), default="")  # 实际用于搜索的关键词/查询
    source_country = Column(String(10), default="")  # 国家代码
    original_keyword = Column(String(500), default="")  # AI 本地化前的原始关键词
    translated_keyword = Column(String(500), default="")  # AI 本地化后的当地语言关键词
    language = Column(String(10), default="")  # 该来源使用的搜索语言（en/de/tr...）
    crawl_time = Column(DateTime, nullable=True)  # 该来源抓取/发现时间
    snippet = Column(Text, default="")  # 搜索结果摘要或页面摘要

    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="company_sources")


class CompanyVerification(Base):
    """真实性验证历史 —— 每次 DNS/HTTP/SSL/MX 验证都留痕，可回溯。

    与 Company 上的 dns_valid/http_status/ssl_valid/mx_valid（最新缓存）互补：
    本表保存完整结构化结果（含 SSL 签发方/过期日、MX 明细）与验证时间。
    """
    __tablename__ = "company_verifications"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    dns_valid = Column(Boolean, nullable=True)
    dns_records = Column(JSON, default=list)  # 解析到的 A / AAAA 等记录
    http_status = Column(Integer, nullable=True)  # 官网 HTTP 状态码（200=可达）
    ssl_valid = Column(Boolean, nullable=True)
    ssl_issuer = Column(String(300), default="")  # SSL 证书签发机构
    ssl_expiry = Column(String(50), default="")  # 证书过期日（ISO 字符串）
    mx_valid = Column(Boolean, nullable=True)
    mx_records = Column(JSON, default=list)  # 邮箱域名 MX 记录
    checked_at = Column(DateTime, nullable=True)  # 验证执行时间

    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="verifications")


class CompanyScore(Base):
    """评分历史 —— 每次评分计算都留痕，便于审计与调参。

    与 Company 上的 score_total/grade/score_breakdown/score_reason（最新缓存）互补。
    """
    __tablename__ = "company_scores"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    total = Column(Float, default=0.0)
    grade = Column(SAEnum(GradeEnum), default=GradeEnum.UNSCORED)
    breakdown = Column(JSON, default=dict)  # 各维度得分明细
    reason = Column(Text, default="")  # 评分理由
    model = Column(String(100), default="")  # 评分引擎/模型标识
    computed_at = Column(DateTime, nullable=True)  # 评分计算时间

    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="scores")


class OutreachDraft(Base):
    """AI生成的沟通草稿，需人工审核确认后才可发送，系统本身不做自动群发"""
    __tablename__ = "outreach_drafts"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    channel = Column(String(20), default="email")  # email / whatsapp
    subject = Column(String(300), default="")
    body = Column(Text, default="")
    status = Column(String(20), default="draft")  # draft / approved / sent / rejected
    created_at = Column(DateTime, default=datetime.utcnow)

    company = relationship("Company", back_populates="outreach_drafts")
