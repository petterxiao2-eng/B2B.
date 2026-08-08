"""Project configuration model - each project is an independent customer development campaign."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, JSON, Boolean, Float
from app.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(200), nullable=False, index=True)
    product_name = Column(String(200), nullable=False)
    product_name_en = Column(String(200), nullable=True)
    product_description = Column(Text, nullable=True)

    # Target market
    target_markets = Column(JSON, nullable=True)  # ["US", "DE", "UK"]
    target_countries = Column(JSON, nullable=True)  # detailed country list

    # Customer type preferences
    priority_customer_types = Column(JSON, nullable=True)
    # ["importer", "distributor", "wholesaler", "brand_owner", "oem", "retailer", "ecommerce"]

    # Delivery & advantages
    delivery_mode = Column(String(100), nullable=True)  # FOB/CIF/DDP etc
    key_advantages = Column(Text, nullable=True)

    # Targets
    target_quantity = Column(Integer, default=100)

    # Keyword matrix (auto-generated)
    keyword_matrix = Column(JSON, nullable=True)
    # {
    #   "product_keywords": [...],
    #   "customer_type_keywords": [...],
    #   "scenario_keywords": [...],
    #   "evidence_keywords": [...],
    #   "region_keywords": [...]
    # }

    # Scoring template override (null = use default)
    scoring_template = Column(JSON, nullable=True)

    # Status
    status = Column(String(20), default="draft")  # draft/active/paused/completed
    last_run_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
