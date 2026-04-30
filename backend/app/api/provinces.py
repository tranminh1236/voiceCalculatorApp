from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models import Province
from app.schemas import ProvinceOut


router = APIRouter(prefix="/api/provinces", tags=["provinces"])


@router.get("", response_model=list[ProvinceOut])
def list_provinces(
    region: str | None = Query(default=None, pattern="^(mb|mt|mn)$"),
    db: Session = Depends(get_db),
):
    q = db.query(Province)
    if region:
        q = q.filter(Province.region == region)
    return q.order_by(Province.region, Province.code).all()
