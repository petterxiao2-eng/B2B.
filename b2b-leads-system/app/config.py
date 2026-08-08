"""
全局配置。使用 pydantic-settings 从环境变量 / .env 文件加载配置。
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # 数据库
    # 默认用 SQLite（免安装数据库，双击/命令行直接跑），适合本地验证效果。
    # 想切到生产环境用 PostgreSQL，把 .env 里的 DATABASE_URL 改成：
    #   postgresql://user:password@host:5432/dbname
    database_url: str = "sqlite:///./b2b_leads.db"

    # 外部服务
    serpapi_key: str = ""
    anthropic_api_key: str = ""
    enable_bing: bool = True  # 是否启用 Bing 搜索（同走 SerpAPI engine=bing，复用 SERPAPI_KEY）

    # 应用
    app_secret_key: str = "dev-secret-change-me"
    environment: str = "development"
    log_level: str = "INFO"

    # 爬虫
    scraper_user_agent: str = "Mozilla/5.0 (compatible; B2BLeadsBot/1.0)"
    scraper_timeout_seconds: int = 15
    scraper_max_concurrent: int = 5

    # 定时任务
    scheduler_enabled: bool = True


settings = Settings()
