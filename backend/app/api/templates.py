import json
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models import Template
from app.schemas import TemplateCreate, TemplateOut, GroupDef


router = APIRouter(prefix="/api/templates", tags=["templates"])


def _to_out(t: Template) -> TemplateOut:
    raw_groups = json.loads(t.groups_json)
    groups = [GroupDef(**g) for g in raw_groups]
    return TemplateOut(id=t.id, name=t.name, groups=groups, created_at=t.created_at)


@router.post("", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
def create_template(body: TemplateCreate, db: Session = Depends(get_db)) -> TemplateOut:
    t = Template(
        name=body.name,
        groups_json=json.dumps([g.model_dump(mode="json") for g in body.groups]),
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return _to_out(t)


@router.get("", response_model=list[TemplateOut])
def list_templates(db: Session = Depends(get_db)) -> list[TemplateOut]:
    return [_to_out(t) for t in db.query(Template).order_by(Template.id.desc()).all()]


@router.get("/{template_id}", response_model=TemplateOut)
def get_template(template_id: int, db: Session = Depends(get_db)) -> TemplateOut:
    t = db.get(Template, template_id)
    if t is None:
        raise HTTPException(status_code=404, detail="template not found")
    return _to_out(t)
