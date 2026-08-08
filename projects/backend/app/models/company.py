"""Company/Customer model - stores all discovered B2B companies."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, JSON, Boolean
from app.database import Base


class Company(Base):
    __tablename__ = "companies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), nullable=False, index=True)

    # Basic info
    company_name = Column(String(300), nullable=False, index=True)
    website = Column(String(500), nullable=True, index=True)
    country = Column(String(100), nullable=True, index=True)
    state_province = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)

    # Business profile
    customer_type = Column(String(100), nullable=True)
    # importer/distributor/wholesaler/brand_owner/oem/retailer/ecommerce/trader
    customer_pool = Column(String(50), nullable=True)  # discovered/verified/active
    main_business = Column(Text, nullable=True)
    related_products = Column(Text, nullable=True)

    # Evidence
    product_match_evidence = Column(Text, nullable=True)
    procurement_capability = Column(Text, nullable=True)
    inventory_channel_capability = Column(Text, nullable=True)

    # Scoring
    score = Column(Float, default=0.0)
    score_details = Column(JSON, nullable=True)
    # {
    #   "product_match": 0-25,
    #   "customer_type_match": 0-20,
    #   "procurement_capability": 0-20,
    #   "business_scale": 0-15,
    #   "market_value": 0-10,
    #   "info_credibility": 0-10
    # }
    grade = Column(String(10), nullable=True, index=True)  # A/B/C/D/excluded

    # Discovery
    discovery_path = Column(String(200), nullable=True)
    source_keywords = Column(Text, nullable=True)
    source_url_1 = Column(String(500), nullable=True)
    source_url_2 = Column(String(500), nullable=True)
    collected_at = Column(DateTime, default=datetime.utcnow)

    # Outreach
    suggested_approach = Column(Text, nullable=True)
    items_to_verify = Column(Text, nullable=True)

    # Review
    review_status = Column(String(20), default="pending")  # pending/approved/rejected
    reviewed_at = Column(DateTime, nullable=True)

    # Background check report
    background_report = Column(JSON, nullable=True)
    # {
    #   "business_scope": "",
    #   "product_lines": [],
    #   "founded_year": null,
    #   "company_size": "",
    #   "main_markets": [],
    #   "branches": [],
    #   "google_maps_verified": false,
    #   "social_media": {"linkedin": "", "facebook": "", "instagram": ""},
    #   "industry_associations": [],
    #   "trade_shows": []
    # }

    # WhatsApp sniffing
    whatsapp_numbers = Column(JSON, nullable=True)  # ["+1234567890"]
    whatsapp_group_links = Column(JSON, nullable=True)  # ["https://chat.whatsapp.com/..."]

    # Customs data
    customs_data = Column(JSON, nullable=True)
    # {
    #   "import_records": 0,
    #   "top_suppliers": [],
    #   "purchase_frequency": "",
    #   "data_source": ""
    # }

    # Dedup
    domain = Column(String(300), nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
