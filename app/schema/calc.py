from pydantic import BaseModel, Field, validator
from typing import List, Optional
from decimal import Decimal

class CommissionRateByYear(BaseModel):
    year: int = Field(..., ge=1, description="Lease year (1 = first year)")
    rate: float = Field(..., ge=0, le=100, description="Commission rate for this year in % (e.g., 5.0)")

class AdvancedCommissionInput(BaseModel):
    gross_area_sf: Decimal = Field(..., gt=0, description="Rentable Square Footage")
    total_term_years: int = Field(..., gt=0, le=30, description="Total lease term in years")

    # Option A: Flat base rent + escalation (most common)
    base_rent_psf_year1: Optional[Decimal] = Field(None, gt=0, description="Starting Face Rent PSF in Year 1")
    annual_escalation_rate: Optional[Decimal] = Field(None, ge=0, description="Annual escalation rate (%)")

    # Option B: Manual per-year rent (for full control)
    rent_psf_per_year: Optional[List[Decimal]] = Field(None, description="List of face rent PSF for each year")

    free_rent_months: Decimal = Field(0, ge=0, description="Total free rent months at beginning")

    # REQUIRED: Variable commission rates per year
    commission_rates: List[CommissionRateByYear] = Field(..., description="Commission % for each year")

    @validator('commission_rates')
    def check_commission_rates_cover_term(cls, v, values):
        term = values.get('total_term_years')
        if term is not None:
            years_provided = {cr.year for cr in v}
            expected_years = set(range(1, term + 1))
            if years_provided != expected_years:
                missing = expected_years - years_provided
                extra = years_provided - expected_years
                error = []
                if missing:
                    error.append(f"Missing years: {sorted(missing)}")
                if extra:
                    error.append(f"Extra years: {sorted(extra)}")
                raise ValueError(f"Commission rates must be provided for exactly years 1 to {term}. {'; '.join(error)}")
        return v

    @validator('rent_psf_per_year', pre=True)
    def check_rent_per_year_length(cls, v, values):
        if v is not None:
            term = values.get('total_term_years')
            if term is not None and len(v) != term:
                raise ValueError(f"rent_psf_per_year must have exactly {term} entries")
        return v

    @validator('*', pre=True)
    def empty_to_none(cls, v):
        if v == '' or v is None:
            return None
        return v


class CommissionYearDetail(BaseModel):
    year: int
    face_rent_psf: Decimal
    gross_annual_rent: Decimal
    free_rent_this_year: Decimal
    commissionable_rent: Decimal
    commission_rate_pct: Decimal
    commission_amount: Decimal

class AdvancedCommissionOutput(BaseModel):
    total_commission_due: Decimal = Field(..., description="Total commission payout over lease term")
    total_commissionable_rent: Decimal = Field(..., description="Sum of all rent on which commission was paid")
    total_free_rent_value: Decimal = Field(..., description="Dollar value of free rent concession")
    annual_breakdown: List[CommissionYearDetail] = Field(..., description="Year-by-year calculation details")

    

from pydantic import BaseModel, Field, validator
from typing import Optional

class LeaseFinanceInput(BaseModel):

    gross_area_sf: float = Field(..., gt=0, description="Rentable Square Footage")
    total_term_years: float = Field(..., gt=0, description="Total lease term in years")
    

    face_rent_psf: Optional[float] = Field(None, gt=0, description="Annual rent per SF in $")
    annual_escalation_rate: Optional[float] = Field(None, ge=0, description="Annual escalation %")
    free_rent_months: Optional[float] = Field(None, ge=0, description="Free rent months")
    ti_allowance_psf: Optional[float] = Field(None, ge=0, description="TI allowance per SF in $")
    commission_rate_per_year: Optional[float] = Field(None, ge=0, description="Commission % per year")
    discount_rate: Optional[float] = Field(None, gt=0, description="Discount rate / IRR %")
    

    commission_rate_total: Optional[float] = Field(None, ge=0, description="Total commission rate %")
    
    @validator('*', pre=True)
    def empty_string_to_none(cls, v):
        if v == '' or v is None:
            return None
        return v


class LeaseFinanceOutput(BaseModel):
    """Output model for lease finance calculations"""
    ner_psf_annual: Optional[float] = Field(None, description="Net Effective Rent per SF per year")
    total_commission_due: Optional[float] = Field(None, description="Total commission payout")
    total_cash_outflow_concessions: Optional[float] = Field(None, description="Total concessions & commission")
    calculation_details: Optional[dict] = Field(None, description="Detailed breakdown")
