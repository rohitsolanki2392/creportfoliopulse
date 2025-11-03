from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from app.models.models import BuildingAccessRequest, BuildingPermission, Status


async def get_building_access_requests_for_user(db: AsyncSession, user_id: int) -> List[BuildingAccessRequest]:
    result = await db.execute(select(BuildingAccessRequest).where(BuildingAccessRequest.user_id == user_id))
    return result.scalars().all()


async def create_lease_access_request(db: AsyncSession, user_id: int, building_id: int) -> BuildingAccessRequest:
    lease_request = BuildingAccessRequest(
        user_id=user_id,
        building_id=building_id,
        status=Status.pending,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(lease_request)
    await db.commit()
    await db.refresh(lease_request)
    return lease_request


async def update_lease_request_status(db: AsyncSession, lease_request: BuildingAccessRequest, action: str) -> BuildingAccessRequest:
    lease_request.status = Status.approved if action == "approve" else Status.denied
    lease_request.updated_at = datetime.utcnow()
    db.add(lease_request)
    await db.commit()
    await db.refresh(lease_request)
    return lease_request



async def create_building_permission(db: AsyncSession, building_id: int, user_id: int) -> BuildingPermission:
    permission = BuildingPermission(
        building_id=building_id,
        user_id=user_id
    )
    db.add(permission)
    await db.commit()
    await db.refresh(permission)
    return permission


async def get_access_requests_by_user_and_status(db: AsyncSession, user_id: int, status: Status) -> List[BuildingAccessRequest]:
    result = await db.execute(
        select(BuildingAccessRequest).where(
            BuildingAccessRequest.user_id == user_id,
            BuildingAccessRequest.status == status
        )
    )
    return result.scalars().all()
