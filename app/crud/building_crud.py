from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List,Optional
from app.models.models import Building
from app.schema.building_schema import BuildingCreate

async def get_building(db: AsyncSession, building_id: int) -> Optional[Building]:
    result = await db.execute(select(Building).where(Building.id == building_id))
    return result.scalars().first()




async def get_all_buildings(
    db: AsyncSession,
    company_id: int,
    category: Optional[str] = None
) -> List[Building]:
    query = select(Building).where(Building.company_id == company_id)
    
    if category:
        query = query.where(Building.category == category)
    
    result = await db.execute(query)
    return result.scalars().all()


async def get_buildings_by_owner(
    db: AsyncSession,
    owner_id: int,
    company_id: int,
    category: Optional[str] = None
) -> List[Building]:
    query = select(Building).where(
        Building.owner_id == owner_id,
        Building.company_id == company_id
    )
    
    if category:
        query = query.where(Building.category == category)
    
    result = await db.execute(query)
    return result.scalars().all()



async def is_building_owner(db: AsyncSession, user_id: int) -> bool:
    result = await db.execute(select(Building).where(Building.owner_id == user_id))
    building = result.scalars().first()
    return building is not None


async def create_buildings(
    db: AsyncSession,
    buildings: List[BuildingCreate],
    owner_id: int,
    company_id: int
) -> List[Building]:
    created_buildings = []
    for building in buildings:
        db_building = Building(
        address=building.address,
        category=building.category, 
        owner_id=owner_id,
        company_id=company_id
    )

        db.add(db_building)
        created_buildings.append(db_building)
    
    await db.commit()
    
    for building in created_buildings:
        await db.refresh(building)
    
    return created_buildings


async def update_building(
    db: AsyncSession,
    building_id: int,
    building_data: BuildingCreate
) -> Optional[Building]:
    result = await db.execute(select(Building).where(Building.id == building_id))
    db_building = result.scalars().first()
    if not db_building:
        return None
    
    db_building.address = building_data.address
    db.add(db_building)
    await db.commit()
    await db.refresh(db_building)
    
    return db_building


async def delete_building(db: AsyncSession, building_id: int) -> bool:
    result = await db.execute(select(Building).where(Building.id == building_id))
    db_building = result.scalars().first()
    if not db_building:
        return False
    
    await db.delete(db_building)
    await db.commit()
    return True
