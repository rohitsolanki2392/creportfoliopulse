from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.crud.client_ingestion_config import get_config_by_company
from app.models.models import SpaceInquiry
from app.schema.client_ingestion_config import ClientIngestionConfigCreate, ClientIngestionConfigUpdate, ClientIngestionConfigOut
from app.schema.space_inquiry import SpaceInquiryOut
from app.services.ingestion_config_service import create_config_service, get_decrypted_config, switch_config_service, update_config_service
from app.database.db import get_db
from app.utils.auth_utils import get_current_user

router = APIRouter()


@router.post("/client-config", status_code=201)
async def create_config(
    payload: ClientIngestionConfigCreate, 
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not allowed")

    existing_cfg = await get_config_by_company(db, current_user.company_id)
    if existing_cfg:
        raise HTTPException(status_code=400, detail="Config already exists for this company")
    
    cfg = await create_config_service(db, payload, current_user.company_id)
    return {
        "message": "Config created successfully", 
        "config": ClientIngestionConfigOut.model_validate(cfg)
    }


@router.patch("/client-config", status_code=200)
async def update_config(
    payload: ClientIngestionConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not allowed")
    
    cfg = await get_decrypted_config(db, current_user.company_id)

    if not cfg:
        raise HTTPException(status_code=404, detail="Config not found")

    updated_cfg = await update_config_service(db, cfg, payload)
    return {
        "message": "Config updated successfully", 
        "config": ClientIngestionConfigOut.model_validate(updated_cfg)
    }


@router.get("/client-config", response_model=ClientIngestionConfigOut)
async def get_config(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not allowed")

    cfg = await get_decrypted_config(db, current_user.company_id)

    if not cfg:
        raise HTTPException(status_code=404, detail="Client config not found")

    return cfg


@router.patch("/client-config/switch", status_code=200)
async def switch_config(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Not allowed")

    cfg = await get_config_by_company(db, current_user.company_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="Config not found")

    await switch_config_service(db, cfg)
    return {"message": "Config deactivated successfully"}


@router.delete("/client-config", status_code=200)
async def delete_config(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    cfg = await get_config_by_company(db, current_user.company_id)
    if not cfg:
        raise HTTPException(status_code=404, detail="Config not found")

    await db.delete(cfg)
    await db.commit()

    return {"message": "Client config & related inquiries deleted successfully"}


@router.get("/list", response_model=List[SpaceInquiryOut])
async def list_inquiries(
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    result = await db.execute(
        select(SpaceInquiry)
        .where(SpaceInquiry.company_id == current_user.company_id)
        .order_by(SpaceInquiry.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/details/{inquiry_id}", response_model=SpaceInquiryOut)
async def get_inquiry(
    inquiry_id: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    result = await db.execute(
        select(SpaceInquiry).where(
            SpaceInquiry.id == inquiry_id,
            SpaceInquiry.company_id == current_user.company_id
        )
    )
    inquiry = result.scalars().first()

    if not inquiry:
        raise HTTPException(404, "Not space inquiry found")

    return inquiry
