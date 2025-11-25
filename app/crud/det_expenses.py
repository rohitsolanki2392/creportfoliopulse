import uuid
from sqlalchemy.future import select
from sqlalchemy import func
from app.models.models import DETExpenseSubmission

def round4(v):
    if v is None:
        return None
    return round(float(v), 4)

async def create_det_expense(db, company_id: int, payload):
    for key, value in payload.items():
        if isinstance(value, (float, int)):
            payload[key] = round4(value)
    
    submission = DETExpenseSubmission(
        company_id=company_id,
        **payload
    )
    db.add(submission)
    await db.commit()
    await db.refresh(submission)
    return submission


async def get_admin_all_submissions(db, company_id: int):
    q = await db.execute(
        select(DETExpenseSubmission).where(
            DETExpenseSubmission.company_id == company_id
        )
    )
    return q.scalars().all()


async def get_benchmark_group(db, company_id, sf_band, submarket, building_class):
    q = await db.execute(
        select(
            func.count(DETExpenseSubmission.id),
            func.avg(DETExpenseSubmission.realestate_taxes_psf),
            func.avg(DETExpenseSubmission.property_insurance_psf),
            func.avg(DETExpenseSubmission.utilities_psf),
            func.avg(DETExpenseSubmission.janitorial_psf),
            func.avg(DETExpenseSubmission.prop_mgmt_fees_psf),
            func.avg(DETExpenseSubmission.security_psf),
            func.avg(DETExpenseSubmission.admin_charges_psf),
            func.avg(DETExpenseSubmission.ti_buildout_psf),
            func.avg(DETExpenseSubmission.capex_major_psf),
            func.avg(DETExpenseSubmission.commission_advert_psf)
        ).where(
            DETExpenseSubmission.company_id == company_id,
            DETExpenseSubmission.building_sf_band == sf_band,
            DETExpenseSubmission.submarket_geo == submarket,
            DETExpenseSubmission.building_class == building_class
        )
    )
    return q.first()
