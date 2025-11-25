from pydantic import BaseModel
from typing import Optional


class DETExpenseBase(BaseModel):
    building_sf_band: str
    submarket_geo: str
    building_class: str
    building_sf: str

    realestate_taxes_psf: float
    property_insurance_psf: float
    utilities_psf: float
    janitorial_psf: float
    prop_mgmt_fees_psf: float
    security_psf: float
    admin_charges_psf: float
    ti_buildout_psf: float
    capex_major_psf: float
    commission_advert_psf: float


class DETExpenseCreate(DETExpenseBase):
    pass


class DETExpenseResponse(DETExpenseBase):
    id: int
    company_id: int

    class Config:
        from_attributes = True


class DETExpenseBenchmarkRequest(BaseModel):
    sf_band: str
    submarket: str
    building_class: str