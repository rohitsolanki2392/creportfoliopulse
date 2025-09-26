
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.crud import building_crud, building_permission_crud
from app.database.db import get_db
from app.schema.building_schema import BuildingCreate, BuildingUpdate
from app.utils.auth_utils import get_current_user
from app.models.models import BuildingAccessRequest, BuildingPermission, User


router = APIRouter()

@router.post("/create_buildings", summary="Create multiple buildings")
def create_buildings(
    buildings: List[BuildingCreate],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    created_buildings = building_crud.create_buildings(db, buildings, current_user.id,current_user.company_id)
    invited_users = db.query(User).filter(User.role == "user").all()
    for building in created_buildings:
        for user in invited_users:
            existing_req = db.query(BuildingAccessRequest).filter(
                BuildingAccessRequest.user_id == user.id,
                BuildingAccessRequest.building_id == building.id
            ).first()

            if not existing_req:
                access_request = building_permission_crud.create_lease_access_request(db, user.id, building.id)
                building_permission_crud.update_lease_request_status(db, access_request, "approve")

            existing_perm = db.query(BuildingPermission).filter(
                BuildingPermission.user_id == user.id,
                BuildingPermission.building_id == building.id
            ).first()

            if not existing_perm:
                building_permission_crud.create_building_permission(db, building.id, user.id)

    db.commit()

    return {
        "message": f"{len(created_buildings)} building(s) created successfully",
        "buildings": [
            {
                "id": b.id,
                "address": b.address,
                "owner_id": b.owner_id
            }
            for b in created_buildings
        ]
    }


@router.get("/list_buildings", summary="List all buildings")
def list_buildings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role == "admin" or building_crud.is_building_owner(db, current_user.id):
        buildings = building_crud.get_buildings_by_owner(db, current_user.id,current_user.company_id)
        return [
            {
                "id": b.id,
                "address": b.address,
                "owner_id": b.owner_id,
                "access_status": "approved"  
            }
            for b in buildings
        ]

    
    buildings = building_crud.get_all_buildings(db,current_user.company_id)
   
    access_requests = building_permission_crud.get_building_access_requests_for_user(db, current_user.id)
    access_map = {req.building_id: req.status.value for req in access_requests}
    

    return [
        {
            "id": b.id,
            "address": b.address,
            "owner_id": b.owner_id,
            "access_status": access_map.get(b.id, "NULL")  
        }
        for b in buildings
    ]

@router.patch("/update_building", summary="Update a building")
def update_building(
    building: BuildingUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    db_building = building_crud.update_building(db, building.building_id, building)
    if not db_building:
        raise HTTPException(status_code=404, detail="Building not found")
    
    return {
        "message": "Building updated successfully",
        "building": {
            "id": db_building.id,
            "address": db_building.address
           
        }
    }

@router.delete("/delete_building/", summary="Delete a building")
def delete_building(
    building_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    deleted = building_crud.delete_building(db, building_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Building not found")
    return {"message": "Building and associated records deleted successfully"}
