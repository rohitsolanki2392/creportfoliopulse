from sqlalchemy.ext.asyncio import AsyncSession
from app.models.models import User
from app.schema.tour import TourCreate
from app.crud.tour import tour_crud

class TourService:

    async def create_tour(self, db: AsyncSession, data: TourCreate, user: User):
        return await tour_crud.create_tour(db, data, user)

    async def list_company_tours(self, db: AsyncSession, user: User):
        return await tour_crud.get_all_company_tours(db, user.company_id)

    
    async def delete_tour(self, db: AsyncSession, tour_id: int, user: User):

        return await tour_crud.delete_tour(db, tour_id, user)

tour_service = TourService()
