from sqlalchemy.orm import Session
from typing import List, Optional
from app.models.models import Building
from app.schema.building_schema import BuildingCreate


def get_building(db: Session, building_id: int) -> Optional[Building]:
    return db.query(Building).filter(Building.id == building_id).first()

def get_all_buildings(db: Session,company_id) -> List[Building]:
    return db.query(Building).filter(Building.company_id==company_id).all()

def get_buildings_by_owner(db: Session, owner_id: int,company_id) -> List[Building]:
    return db.query(Building).filter(Building.owner_id == owner_id).all()

def is_building_owner(db: Session, user_id: int) -> bool:
    return db.query(Building).filter(Building.owner_id == user_id).first() is not None

def create_buildings(db: Session, buildings: List[BuildingCreate], owner_id: int,company_id:int) -> List[Building]:
    created_buildings = []
    for building in buildings:
        db_building = Building(
            address=building.address,
            owner_id=owner_id,
            company_id= company_id,
        )
        db.add(db_building)
        created_buildings.append(db_building)
    db.commit()
    for building in created_buildings:
        db.refresh(building)
    return created_buildings

def update_building(db: Session, building_id: int, building_data: BuildingCreate) -> Building:
    db_building = db.query(Building).filter(Building.id == building_id).first()
    if not db_building:
        return None
    
    db_building.address = building_data.address
    db.commit()
    db.refresh(db_building)
    return db_building

def delete_building(db: Session, building_id: int) -> bool:
    db_building = db.query(Building).filter(Building.id == building_id).first()
    if not db_building:
        return False
    db.delete(db_building)
    db.commit()
    return True








