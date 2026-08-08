from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from app.config import settings

# SQLite 默认不允许跨线程复用同一个连接，但 FastAPI 的 BackgroundTasks
# （搜索任务的后台pipeline）会在不同线程里访问数据库，所以SQLite下必须加这个参数。
# 用 PostgreSQL/MySQL 等其他数据库时不需要这个参数，所以只在检测到sqlite时加上。
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
    connect_args=connect_args,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI 依赖注入：每次请求一个数据库会话，用完自动关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
