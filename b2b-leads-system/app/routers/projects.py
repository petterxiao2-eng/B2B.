from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.services.scoring import DEFAULT_WEIGHTS, DEFAULT_GRADE_THRESHOLDS

router = APIRouter(prefix="/api/projects", tags=["projects"])


@router.post("", response_model=schemas.ProjectOut)
def create_project(payload: schemas.ProjectCreate, db: Session = Depends(get_db)):
    project = models.Project(
        name=payload.name,
        description=payload.description,
        target_regions=payload.target_regions,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    # 自动创建默认评分模板，方便直接使用，之后可在Dashboard里调整权重
    template = models.ScoringTemplate(
        project_id=project.id,
        weights=DEFAULT_WEIGHTS,
        grade_thresholds=DEFAULT_GRADE_THRESHOLDS,
    )
    db.add(template)
    db.commit()

    return project


@router.get("", response_model=list[schemas.ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return db.query(models.Project).order_by(models.Project.created_at.desc()).all()


@router.get("/{project_id}", response_model=schemas.ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(models.Project).get(project_id)
    if not project:
        raise HTTPException(404, "项目不存在")
    return project


@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = db.query(models.Project).get(project_id)
    if not project:
        raise HTTPException(404, "项目不存在")
    db.delete(project)
    db.commit()
    return {"ok": True}


@router.put("/{project_id}/scoring-template")
def update_scoring_template(project_id: int, payload: schemas.ScoringTemplateUpdate, db: Session = Depends(get_db)):
    template = db.query(models.ScoringTemplate).filter_by(project_id=project_id).first()
    if not template:
        raise HTTPException(404, "该项目还没有评分模板")
    template.weights = payload.weights
    template.grade_thresholds = payload.grade_thresholds
    db.commit()
    return {"ok": True}


@router.get("/{project_id}/scoring-template")
def get_scoring_template(project_id: int, db: Session = Depends(get_db)):
    template = db.query(models.ScoringTemplate).filter_by(project_id=project_id).first()
    if not template:
        raise HTTPException(404, "该项目还没有评分模板")
    return {"weights": template.weights, "grade_thresholds": template.grade_thresholds}
