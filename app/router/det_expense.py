from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.schema.det_expenses import DETExpenseCreate, DETExpenseResponse
from app.crud.det_expenses import create_det_expense, get_all_submissions, round4
from app.crud.det_expenses import get_benchmark_group
from app.database.db import get_db
from app.models.models import User
from app.utils.auth_utils import get_current_user

router = APIRouter()


@router.post("/submit", response_model=DETExpenseResponse)
async def submit_det_expense(
    payload: DETExpenseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(403, "Admin access required")

    data = await create_det_expense(db, current_user.company_id, payload.dict())
    return data


@router.get("/submissions")
async def get_submissions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if current_user.role != "admin":
        raise HTTPException(403, "Admin access required")

    return await get_all_submissions(db)


@router.get("/benchmark")
async def get_det_benchmark(
    sf_band: str,
    submarket: str,
    building_class: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await get_benchmark_group(db, current_user.company_id, sf_band, submarket, building_class)

    (
        count,
        avg_insurance,
        avg_electric,
        avg_gas,
        avg_water,
        avg_janitorial,
        avg_mgmt,
        avg_lobby,
        avg_monitoring,
        avg_accounting,
        avg_legal,
        avg_ti,
        avg_comm,
        avg_interest,
        avg_tax
    ) = result

    return {
        "sf_band": sf_band,
        "submarket": submarket,
        "building_class": building_class,
        "data_points": count,
        "benchmark": {
            "property_insurance_psf": round4(avg_insurance),
            "electric_psf": round4(avg_electric),
            "gas_psf": round4(avg_gas),
            "water_psf": round4(avg_water),
            "janitorial_cleaning_psf": round4(avg_janitorial),
            "property_mgmt_fees_psf": round4(avg_mgmt),
            "lobby_attendant_security_psf": round4(avg_lobby),
            "security_monitoring_systems_psf": round4(avg_monitoring),
            "accounting_psf": round4(avg_accounting),
            "legal_psf": round4(avg_legal),
            "ti_allowances_psf": round4(avg_ti),
            "commissions_psf": round4(avg_comm),
            "interest_rates_psf": round4(avg_interest),
            "realestate_taxes_psf": round4(avg_tax)
        }
    }