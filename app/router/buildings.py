from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from fastapi import Query
from typing import Optional
from app.crud import building_crud
from app.database.db import get_db
from app.schema.building_schema import BuildingCreate, BuildingUpdate
from app.utils.auth_utils import get_current_user
from app.models.models import User

router = APIRouter()


@router.post("/create_buildings", summary="Create multiple buildings")
async def create_buildings(
    buildings: List[BuildingCreate],
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

  
    created_buildings = await building_crud.create_buildings(
        db, buildings, current_user.id, current_user.company_id
    )

    return {
        "message": f"{len(created_buildings)} building(s) created successfully",
        "buildings": [
            {
                "id": b.id,
                "address": b.address,
                "category": b.category,  
                "owner_id": b.owner_id
            }
            for b in created_buildings
        ]
    }



@router.get("/list_buildings", summary="List all buildings")
async def list_buildings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    category: Optional[str] = Query(None, description="Filter buildings by category")
):
    if current_user.role == "admin" or await building_crud.is_building_owner(db, current_user.id):
        buildings = await building_crud.get_buildings_by_owner(
            db, current_user.id, current_user.company_id, category
        )
    else:
        buildings = await building_crud.get_all_buildings(
            db, current_user.company_id, category
        )

    return [
        {
            "id": b.id,
            "address": b.address,
            "category": b.category,
            "owner_id": b.owner_id,
            "access_status": "approved"
        }
        for b in buildings
    ]

@router.patch("/update_building", summary="Update a building")
async def update_building(
    building: BuildingUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    db_building = await building_crud.update_building(db, building.building_id, building)
    if not db_building:
        raise HTTPException(status_code=404, detail="Building not found")

    return {
        "message": "Building updated successfully",
        "building": {"id": db_building.id, "address": db_building.address}
    }


@router.delete("/delete_building/", summary="Delete a building")
async def delete_building(
    building_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    deleted = await building_crud.delete_building(db, building_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Building not found")
    return {"message": "Building and associated records deleted successfully"}
