# app/router/deal_traker.py

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from sqlalchemy.orm import selectinload
from app.database.db import get_db
from app.models.models import Deal, DealStage, User
from app.schema.deal_traker import DealCreate, DealOut
from app.utils.auth_utils import get_current_user

router = APIRouter(prefix="/deals", tags=["Deal Tracker"])


def get_current_status(stages: List[DealStage]) -> str:
    completed = [s for s in sorted(stages, key=lambda x: x.order_index) if s.is_completed]
    return completed[-1].stage_name if completed else "Not Started"


@router.get("/", response_model=List[DealOut])
async def get_all_deals(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Deal)
        .options(selectinload(Deal.stages), selectinload(Deal.updated_by))
        .where(Deal.company_id == current_user.company_id)
        .order_by(Deal.updated_at.desc())
    )
    deals = result.scalars().unique().all()

    return [
        DealOut(
            id=deal.id,
            tenant_name=deal.tenant_name,
            building_address_interest=deal.building_address_interest,
            current_building_address=deal.current_building_address,
            floor_suite_interest=deal.floor_suite_interest,
            floor_suite_current=deal.floor_suite_current,
            broker_of_record=deal.broker_of_record,
            landlord_lead_of_record=deal.landlord_lead_of_record,
            current_lease_expiration=deal.current_lease_expiration,
            status=get_current_status(deal.stages),
            last_updated=deal.updated_at,
            last_edited_by=deal.updated_by.name if deal.updated_by else "Unknown",
            stages=deal.stages
        )
        for deal in deals
    ]


@router.post("/", response_model=DealOut, status_code=status.HTTP_201_CREATED)
async def create_deal(
    payload: DealCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    new_deal = Deal(
        **payload.model_dump(exclude={"stages"}),
        company_id=current_user.company_id,
        created_by_id=current_user.id,
        updated_by_id=current_user.id,
    )
    db.add(new_deal)
    await db.flush()

    for idx, s in enumerate(payload.stages):
        db.add(DealStage(
            deal_id=new_deal.id,
            stage_name=s.stage_name,
            order_index=idx + 1,
            is_completed=s.is_completed,
            completed_at=s.completed_at,
            notes=s.notes,
        ))

    await db.commit()
    await db.refresh(new_deal, ["stages"])

    return DealOut(
        id=new_deal.id,
        tenant_name=new_deal.tenant_name,
        building_address_interest=new_deal.building_address_interest,
        current_building_address=new_deal.current_building_address,
        floor_suite_interest=new_deal.floor_suite_interest,
        floor_suite_current=new_deal.floor_suite_current,
        broker_of_record=new_deal.broker_of_record,
        landlord_lead_of_record=new_deal.landlord_lead_of_record,
        current_lease_expiration=new_deal.current_lease_expiration,
        status=get_current_status(new_deal.stages),
        last_updated=new_deal.updated_at,
        last_edited_by=current_user.name,  # सही तरीका
        stages=new_deal.stages
    )


@router.get("/{deal_id}", response_model=DealOut)
async def get_deal(
    deal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Deal)
        .options(selectinload(Deal.stages), selectinload(Deal.updated_by))
        .where(Deal.id == deal_id, Deal.company_id == current_user.company_id)
    )
    deal = result.scalars().first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    return DealOut(
        id=deal.id,
        tenant_name=deal.tenant_name,
        building_address_interest=deal.building_address_interest,
        current_building_address=deal.current_building_address,
        floor_suite_interest=deal.floor_suite_interest,
        floor_suite_current=deal.floor_suite_current,
        broker_of_record=deal.broker_of_record,
        landlord_lead_of_record=deal.landlord_lead_of_record,
        current_lease_expiration=deal.current_lease_expiration,
        status=get_current_status(deal.stages),
        last_updated=deal.updated_at,
        last_edited_by=deal.updated_by.name
        if deal.updated_by else "Unknown",
        stages=deal.stages
    )


@router.put("/{deal_id}", response_model=DealOut)
async def update_deal(
    deal_id: int,
    payload: DealCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Deal)
        .options(selectinload(Deal.stages))
        .where(Deal.id == deal_id, Deal.company_id == current_user.company_id)
    )
    deal = result.scalars().first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")


    for key, value in payload.model_dump(exclude={"stages"}).items():
        setattr(deal, key, value)

    deal.updated_by_id = current_user.id

    # Replace all stages
    await db.execute(delete(DealStage).where(DealStage.deal_id == deal.id))
    for idx, s in enumerate(payload.stages):
        db.add(DealStage(
            deal_id=deal.id,
            stage_name=s.stage_name,
            order_index=idx + 1,
            is_completed=s.is_completed,
            completed_at=s.completed_at if s.is_completed else None,
            notes=s.notes,
        ))

    await db.commit()
    await db.refresh(deal, ["updated_at"])  

    return DealOut(
        id=deal.id,
        tenant_name=deal.tenant_name,
        building_address_interest=deal.building_address_interest,
        current_building_address=deal.current_building_address,
        floor_suite_interest=deal.floor_suite_interest,
        floor_suite_current=deal.floor_suite_current,
        broker_of_record=deal.broker_of_record,
        landlord_lead_of_record=deal.landlord_lead_of_record,
        current_lease_expiration=deal.current_lease_expiration,
        status=get_current_status(deal.stages),
        last_updated=deal.updated_at,
        last_edited_by=current_user.name,   
        stages=deal.stages
    )


@router.delete("/{deal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_deal(
    deal_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(
        select(Deal).where(Deal.id == deal_id, Deal.company_id == current_user.company_id)
    )
    deal = result.scalars().first()
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")

    await db.delete(deal)
    await db.commit()
    return None  