import logging

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware

from app.database import Base, engine
from app.config import settings
from app.routers import projects, keywords, search, companies, export, outreach, meta
from app.scheduler import start_scheduler

logging.basicConfig(level=settings.log_level)
logger = logging.getLogger("main")

app = FastAPI(title="跨境B2B客户增长系统", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境建议改成你的Dashboard实际域名
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(keywords.router)
app.include_router(search.router)
app.include_router(companies.router)
app.include_router(export.router)
app.include_router(outreach.router)
app.include_router(meta.router)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")


@app.on_event("startup")
def on_startup():
    # MVP阶段直接用 create_all 建表；后续数据结构变动频繁后建议切换到 alembic migration
    Base.metadata.create_all(bind=engine)
    start_scheduler()
    logger.info("应用启动完成")


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/")
def dashboard(request: Request):
    return templates.TemplateResponse(request, "dashboard.html")
