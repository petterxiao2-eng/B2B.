"""
全局元数据接口（Phase 7）。

为前端提供：
- /api/meta/countries     支持的国家切换器（来自 country_matrix.supported_countries）
- /api/meta/customer-tiers  客户类型分层（Tier1/2/3，来自 search_matrix.CUSTOMER_TYPE_TIERS）

这些配置与具体项目无关，前端在初始化时拉取一次即可，用于"国家切换器"与"客户类型分层"选择。
"""
from fastapi import APIRouter

from app.services.country_matrix import supported_countries
from app.services.search_matrix import CUSTOMER_TYPE_TIERS

router = APIRouter(prefix="/api/meta", tags=["meta"])


@router.get("/countries")
def meta_countries():
    """支持的国家列表，供前端国家切换器渲染。"""
    return supported_countries()


@router.get("/customer-tiers")
def meta_customer_tiers():
    """客户类型分层定义，供前端勾选启用哪些 Tier。"""
    return CUSTOMER_TYPE_TIERS
