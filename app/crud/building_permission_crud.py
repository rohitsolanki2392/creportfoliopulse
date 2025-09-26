
from datetime import datetime
from sqlalchemy.orm import Session
from typing import List, Optional

from app.models.models import BuildingAccessRequest, BuildingPermission, Status

def get_building_access_requests_for_user(db: Session, user_id: int) -> List[BuildingAccessRequest]:
    return db.query(BuildingAccessRequest).filter(BuildingAccessRequest.user_id == user_id).all()


def create_lease_access_request(db: Session, user_id: int, building_id: int):
    lease_request = BuildingAccessRequest(
        user_id=user_id,
        building_id=building_id,
        status=Status.pending,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(lease_request)
    db.commit()
    db.refresh(lease_request)
    return lease_request

def update_lease_request_status(db: Session, lease_request: BuildingAccessRequest, action: str):
    lease_request.status = Status.approved if action == "approve" else Status.denied
    lease_request.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(lease_request)
    return lease_request

def create_building_permission(db: Session, building_id: int, user_id: int):
    permission = BuildingPermission(
        building_id=building_id,
        user_id=user_id
    )
    db.add(permission)
    db.commit()
    return permission


def get_access_requests_by_user_and_status(db: Session, user_id: int, status: Status):
    return db.query(BuildingAccessRequest).filter(
        BuildingAccessRequest.user_id == user_id,
        BuildingAccessRequest.status == status
    ).all()

