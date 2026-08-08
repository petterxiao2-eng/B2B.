"""
国家矩阵（Phase 3）。

为目标国家提供统一的搜索配置：
- gl / hl：Google 地理定位与界面语言
- bing_cc：Bing 市场代码
- google_domain：本地化 Google 域名（展示/可选直连用）
- locale / lang：本地化语言；关键词默认英文，深度模式用 lang 做本地化翻译

所有国家共用同一套查询生成逻辑（见 search_matrix），本模块只负责"国家 -> 搜索参数"的映射，
因此切换国家会自动改变搜索语言、domain 与（深度模式下的）关键词组合。
"""
from dataclasses import dataclass


@dataclass
class CountryProfile:
    code: str
    name: str
    gl: str               # Google 地理定位（serpapi gl）
    hl: str               # 界面语言（serpapi hl）
    bing_cc: str          # Bing 市场代码（mkt / cc）
    google_domain: str    # 本地化 Google 域名
    locale: str           # 本地化 locale
    lang: str             # 默认搜索语言代码（深度模式下用于 AI 本地化关键词）
    notes: str = ""


# 支持的国家（持续扩充）。国家代码采用 ISO-3166 两位大写。
COUNTRY_PROFILES: dict[str, CountryProfile] = {
    "DE": CountryProfile("DE", "Germany", "de", "de", "DE", "google.de", "de-DE", "de"),
    "QA": CountryProfile("QA", "Qatar", "qa", "en", "QA", "google.qa", "en-QA", "en"),
    "TR": CountryProfile("TR", "Turkey", "tr", "tr", "TR", "google.com.tr", "tr-TR", "tr"),
    "EG": CountryProfile("EG", "Egypt", "eg", "en", "EG", "google.com.eg", "en-EG", "en"),
    "SA": CountryProfile("SA", "Saudi Arabia", "sa", "en", "SA", "google.com.sa", "en-SA", "en",
                         notes="阿拉伯语为主，但 B2B 采购多用英文搜索"),
    "AE": CountryProfile("AE", "UAE", "ae", "en", "AE", "google.ae", "en-AE", "en"),
    "US": CountryProfile("US", "United States", "us", "en", "US", "google.com", "en-US", "en"),
    "GB": CountryProfile("GB", "United Kingdom", "uk", "en", "GB", "google.co.uk", "en-GB", "en"),
    "FR": CountryProfile("FR", "France", "fr", "fr", "FR", "google.fr", "fr-FR", "fr"),
    "IT": CountryProfile("IT", "Italy", "it", "it", "IT", "google.it", "it-IT", "it"),
    "ES": CountryProfile("ES", "Spain", "es", "es", "ES", "google.es", "es-ES", "es"),
    "BR": CountryProfile("BR", "Brazil", "br", "pt", "BR", "google.com.br", "pt-BR", "pt"),
    "IN": CountryProfile("IN", "India", "in", "en", "IN", "google.co.in", "en-IN", "en"),
    "JP": CountryProfile("JP", "Japan", "jp", "ja", "JP", "google.co.jp", "ja-JP", "ja"),
}

DEFAULT_COUNTRY = "US"


def get_country(code: str) -> CountryProfile:
    """根据国家代码返回配置；未知代码回退到默认国家（不改变行为，避免搜索失败）。"""
    return COUNTRY_PROFILES.get((code or "").upper(), COUNTRY_PROFILES[DEFAULT_COUNTRY])


def supported_countries() -> list[dict]:
    """供前端国家切换器渲染。"""
    return [
        {"code": p.code, "name": p.name, "lang": p.lang, "google_domain": p.google_domain}
        for p in COUNTRY_PROFILES.values()
    ]
