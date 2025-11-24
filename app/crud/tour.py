from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.models import Tour, User
from datetime import timezone

class TourCRUD:

    async def create_tour(self, db: AsyncSession, data, user: User):
        new_tour = Tour(
            date=data.date if data.date.tzinfo else data.date.replace(tzinfo=timezone.utc),
            building=data.building,
            floor_suite=data.floor_suite,
            tenant=data.tenant,
            broker=data.broker,
            notes=data.notes,
            user_id=user.id,
            company_id=user.company_id
        )

        db.add(new_tour)
        await db.commit()
        await db.refresh(new_tour)

        new_tour.user_email = user.email
        return new_tour

    async def get_all_company_tours(self, db: AsyncSession, company_id: int, current_user_id: int):
        query = (
            select(Tour)
            .where(Tour.company_id == company_id)
            .where(Tour.user_id != current_user_id)              
        )

        result = await db.execute(query)
        tours = result.scalars().all()

        for tour in tours:
            tour.user_email = (await db.get(User, tour.user_id)).email

        return tours
    

    async def delete_tour(self, db: AsyncSession, tour_id: int, user):
        query = select(Tour).where(Tour.id == tour_id)
        result = await db.execute(query)
        tour = result.scalar_one_or_none()

        if not tour:
            return False

        if user.role != "admin" and tour.user_id != user.id:
            return False

        await db.delete(tour)
        await db.commit()
        return True

tour_crud = TourCRUD()
