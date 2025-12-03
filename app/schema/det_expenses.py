from pydantic import BaseModel
from typing import Optional


class DETExpenseBase(BaseModel):
    building_sf_band: Optional[str] = None
    submarket_geo: str
    building_class: str

    realestate_taxes_psf: float
    property_insurance_psf: float
    electric_psf: float
    gas_psf: float
    water_psf: float
    janitorial_cleaning_psf: float
    property_mgmt_fees_psf: float
    lobby_security_psf: float
    security_monitoring_psf: float
    accounting_psf: float
    legal_psf: float
    ti_allowances_psf: float
    commissions_psf: float
    interest_rates_psf: float


class DETExpenseCreate(DETExpenseBase):
    pass


class DETExpenseResponse(DETExpenseBase):
    id: int
    company_id: int

    class Config:
        from_attributes = True

