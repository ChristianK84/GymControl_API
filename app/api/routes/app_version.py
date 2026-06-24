from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.dependencies import require_admin
from app.core.audit import audit_log
from app.core.database import get_db
from app.models.app_versions import AppVersion

router = APIRouter(prefix="/app", tags=["app_version"])


class AppVersionResponse(BaseModel):
    version: str
    version_code: int
    bundle_url: str
    release_notes: str | None


class AppVersionCreate(BaseModel):
    version: str
    version_code: int
    bundle_url: str
    release_notes: str | None = None


@router.get("/version/{platform}", response_model=AppVersionResponse)
def get_latest_version(platform: str, db: Session = Depends(get_db)):
    version = (
        db.query(AppVersion)
        .filter(AppVersion.platform == platform)
        .order_by(AppVersion.id.desc())
        .first()
    )
    if not version:
        raise HTTPException(status_code=404, detail=f"No version found for platform: {platform}")
    return AppVersionResponse(
        version=version.version,
        version_code=version.version_code,
        bundle_url=version.bundle_url,
        release_notes=version.release_notes,
    )


@router.put("/version/{platform}", response_model=AppVersionResponse, status_code=201)
def publish_version(platform: str, payload: AppVersionCreate, db: Session = Depends(get_db), _admin=Depends(require_admin)):
    version = AppVersion(
        platform=platform,
        version=payload.version,
        version_code=payload.version_code,
        bundle_url=payload.bundle_url,
        release_notes=payload.release_notes,
    )
    db.add(version)
    db.commit()
    db.refresh(version)

    audit_log(db, _admin.id, "CREATE", "app_version", version.id,
              f"{_admin.username} publicó versión {payload.version} para {platform}")

    return AppVersionResponse(
        version=version.version,
        version_code=version.version_code,
        bundle_url=version.bundle_url,
        release_notes=version.release_notes,
    )
