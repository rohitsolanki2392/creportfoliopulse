
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from collections import defaultdict
# from apt.crud import lease_crud
from app.models.models import Building, BuildingAccessRequest, Status, User, BuildingPermission
from app.crud import building_crud, building_permission_crud # Updated impor
from app.schema.permission_schema import BuildingAccessRequestAction, BuildingAccessRequestCreate

async def request_building_access_service(request: BuildingAccessRequestCreate, current_user: User, db: Session):
    building = building_crud.get_building(db, request.building_id)
    if not building:
        raise HTTPException(status_code=404, detail="Building not found")

    if building_permission_crud.check_existing_access_request(db, current_user.id, request.building_id, "pending"):
        raise HTTPException(status_code=400, detail="You already have a pending building access request")
    if building_permission_crud.check_existing_access_request(db, current_user.id, request.building_id, "approved"):
        raise HTTPException(status_code=400, detail="You already have approved access to this building")
    if building_permission_crud.check_existing_access_request(db, current_user.id, request.building_id, "denied"):
        raise HTTPException(status_code=400, detail="Your previous request for this building was denied. Please contact an admin")

    access_request = building_permission_crud.create_lease_access_request(db, current_user.id, request.building_id)
    return {
        "message": "Building access request submitted successfully",
        "request_id": access_request.id,
        "user_id": current_user.id,
        "user_email": current_user.email,
        "building_id": access_request.building_id,
        # "building_name": building.building_name,
        "status": access_request.status.value if hasattr(access_request.status, "value") else access_request.status,
        "created_at": access_request.created_at,
        "updated_at": access_request.updated_at
    }

async def action_building_request_service(request: BuildingAccessRequestAction, current_user: User, db: Session):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    if request.action not in ["approve", "deny"]:
        raise HTTPException(status_code=400, detail="Invalid action. Please use 'approve' or 'deny'")

    access_request = building_permission_crud.get_lease_request_by_id(db, request.request_id)
    if not access_request:
        raise HTTPException(status_code=404, detail="Building access request not found")
    if access_request.status.value != "pending":
        raise HTTPException(status_code=400, detail="This request is not pending and cannot be actioned")

    access_request = building_permission_crud.update_lease_request_status(db, access_request, request.action)
    if request.action == "approve":
        building_permission_crud.create_building_permission(db, access_request.building_id, access_request.user_id)

    building = building_crud.get_building(db, access_request.building_id)
    action_message = "Building access request approved successfully" if request.action == "approve" else "Building access request denied successfully"
    return {
        "message": action_message,
        "request_id": access_request.id,
        "user_id": access_request.user_id,
        "user_email": db.query(User).filter(User.id == access_request.user_id).first().email,
        "building_id": access_request.building_id,
        # "building_name": building.building_name if building else None,
        "status": access_request.status.value if hasattr(access_request.status, "value") else access_request.status,
        "created_at": access_request.created_at,
        "updated_at": access_request.updated_at
    }

async def list_access_requests_by_status_service(
    current_user: User,
    db: Session,
    status: Status
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    all_requests = building_permission_crud.get_access_requests_by_exact_status(db, status)

    grouped_users = defaultdict(lambda: {
        "user_id": None,
        "user_name": None,
        "email": None,
        "requested_buildings": []
    })

    for req in all_requests:
        user = req.user
        building = req.building
        if not user:
            continue

        if grouped_users[user.id]["user_id"] is None:
            grouped_users[user.id]["user_id"] = user.id
            grouped_users[user.id]["user_name"] = user.name
            grouped_users[user.id]["email"] = user.email

        grouped_users[user.id]["requested_buildings"].append({
            "request_id": req.id,
            "building_id": building.id if building else None,
            # "building_name": building.building_name if building else None,
            "status": req.status.value if req.status else None,
            "created_at": req.created_at,
            "updated_at": req.updated_at
        })

    return list(grouped_users.values())

async def list_user_access_requests_by_status_service(
    current_user: User,
    db: Session,
    status: Status
):
    # Fetch requests for the current user and the given status
    user_requests = building_permission_crud.get_access_requests_by_user_and_status(
        db=db,
        user_id=current_user.id,
        status=status
    )

    return [
        {
            "request_id": req.id,
            "id": req.building.id if req.building else None,
            # "building_name": req.building.building_name if req.building else None,
            "address": req.building.address if req.building else None,
            # "year": req.building.year if req.building else None,
            "owner_id": req.building.owner_id if req.building else None,
            "access_status": req.status.value if req.status else None
        }
        for req in user_requests
    ]

async def list_user_null_access_buildings_service(
    current_user: User,
    db: Session
):
    # Fetch all buildings where user has no access request
    buildings = db.query(Building).filter(
        ~Building.id.in_(
            db.query(BuildingAccessRequest.building_id).filter(
                BuildingAccessRequest.user_id == current_user.id
            )
        )
    ).all()

    return [
        {
            "id": building.id,
            # "building_name": building.building_name,
            "address": building.address,
            # "year": building.year,
            "owner_id": building.owner_id,
            "access_status": None
        }
        for building in buildings
    ]

def get_access_requests_by_user_and_status(db: Session, user_id: int, status: Status):
    return db.query(BuildingAccessRequest).filter(
        BuildingAccessRequest.user_id == user_id,
        BuildingAccessRequest.status == status
    ).all()

async def grant_all_buildings_permission(user_id: int, db: Session):
    # Fetch all buildings
    all_buildings = db.query(Building).all()
    
    for building in all_buildings:
        # Check if permission already exists
        existing_permission = db.query(BuildingPermission).filter(
            BuildingPermission.building_id == building.id,
            BuildingPermission.user_id == user_id
        ).first()
        
        if not existing_permission:
            # Create new permission
            building_permission_crud.create_building_permission(db, building.id, user_id)
    
    db.commit()