from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.schema.det_expenses import DETExpenseCreate, DETExpenseResponse, DETExpenseBenchmarkRequest
from app.crud.det_expenses import create_det_expense, get_admin_all_submissions, round4
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

    return await get_admin_all_submissions(db, current_user.company_id)


@router.get("/benchmark")
async def get_det_benchmark(
    request: DETExpenseBenchmarkRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):

    (
        count,
        avg_tax,
        avg_insurance,
        avg_util,
        avg_jan,
        avg_mgmt,
        avg_sec,
        avg_admin,
        avg_ti,
        avg_capex,
        avg_comm
    ) = await get_benchmark_group(db, current_user.company_id, request.sf_band, request.submarket, request.building_class)

    if count < 10:
        return {"message": "Insufficient Data for Benchmark"}

    return {
        "sf_band": request.sf_band,
        "submarket": request.submarket,
        "building_class": request.building_class,
        "data_points": count,
        "benchmark": {
            "realestate_taxes_psf": round4(avg_tax),
            "property_insurance_psf": round4(avg_insurance),
            "utilities_psf": round4(avg_util),
            "janitorial_psf": round4(avg_jan),
            "prop_mgmt_fees_psf": round4(avg_mgmt),
            "security_psf": round4(avg_sec),
            "admin_charges_psf": round4(avg_admin),
            "ti_buildout_psf": round4(avg_ti),
            "capex_major_psf": round4(avg_capex),
            "commission_advert_psf": round4(avg_comm),
        }
    }
