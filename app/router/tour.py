from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.db import get_db
from app.models.models import User
from app.schema.tour import TourCreate, TourResponse
from app.utils.auth_utils import get_current_user
from app.services.tour import tour_service

router = APIRouter()

@router.post("/", response_model=TourResponse)
async def create_tour(
    tour_data: TourCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    return await tour_service.create_tour(db, tour_data, user)

@router.get("/", response_model=list[TourResponse])
async def list_company_tours(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):
    return await tour_service.list_company_tours(db, user)



@router.delete("/{tour_id}", status_code=status.HTTP_200_OK)
async def delete_tour(
    tour_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user)
):

    deleted = await tour_service.delete_tour(db, tour_id, user)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tour not found or not authorized to delete"
        )
    return {"message": "Tour deleted successfully"}
