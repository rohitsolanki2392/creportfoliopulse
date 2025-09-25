
from datetime import datetime
from sqlalchemy.orm import Session
from typing import List, Optional

from app.models.models import BuildingAccessRequest, BuildingPermission, Status


def get_building_permission(db: Session, user_id: int, building_id: int) -> Optional[BuildingPermission]:
    return db.query(BuildingPermission).filter_by(
        user_id=user_id, building_id=building_id
    ).first()

def get_building_access_requests_for_user(db: Session, user_id: int) -> List[BuildingAccessRequest]:
    return db.query(BuildingAccessRequest).filter(BuildingAccessRequest.user_id == user_id).all()

def check_existing_access_request(db: Session, user_id: int, building_id: int, status: str) -> Optional[BuildingAccessRequest]:
    return db.query(BuildingAccessRequest).filter(
        BuildingAccessRequest.user_id == user_id,
        BuildingAccessRequest.building_id == building_id,
        BuildingAccessRequest.status == status
    ).first()

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


def get_all_access_requests(db: Session, status: str = None):
    query = db.query(BuildingAccessRequest)
    if status:
        query = query.filter(BuildingAccessRequest.status == status)
    return query.all()

def get_access_requests_by_exact_status(db: Session, status: Status):
    return db.query(BuildingAccessRequest).filter(BuildingAccessRequest.status == status).all()


def get_lease_request_by_id(db: Session, request_id: int) -> Optional[BuildingAccessRequest]:
    return db.query(BuildingAccessRequest).filter(BuildingAccessRequest.id == request_id).first()

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

