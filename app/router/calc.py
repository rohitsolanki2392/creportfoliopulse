# file: main.py
from fastapi import APIRouter
from decimal import Decimal, ROUND_HALF_UP
from pydantic import BaseModel, Field
from typing import List, Optional

class CommissionRatePerYear(BaseModel):
    year: int = Field(..., ge=1, description="Year number (1,2,3...)")
    rate: Decimal = Field(..., gt=0, le=100, description="Commission % for this year (e.g. 5.0)")

class LeaseInput(BaseModel):
    square_footage: Decimal = Field(..., gt=0)
    total_term_years: int = Field(..., ge=1, le=50)
    base_rent_psf: Decimal = Field(..., gt=0)

    annual_escalation_rate: Optional[Decimal] = Field(None, ge=0, le=50)
    free_rent_months: Optional[int] = Field(0, ge=0)
    ti_allowance_psf: Optional[Decimal] = Field(Decimal('0'), ge=0)
    discount_rate: Optional[Decimal] = Field(Decimal('8.0'), gt=0)


    commission_rates: List[CommissionRatePerYear] = Field(
        ..., 
        min_length=1,
        description="Commission rate har saal ke liye – total_term_years jitne hone chahiye"
    )

    simple_commission_total_pct: Optional[Decimal] = None

 
    from pydantic import model_validator

    @model_validator(mode='after')
    def check_commission_rates_count(self):
        if len(self.commission_rates) != self.total_term_years:
            raise ValueError(f"Commission rates {len(self.commission_rates)} diye, par lease {self.total_term_years} saal ka hai!")
        expected_years = set(range(1, self.total_term_years + 1))
        given_years = {item.year for item in self.commission_rates}
        if given_years != expected_years:
            raise ValueError("Commission rates mein saare years 1 se last year tak hone chahiye!")
        return self
    
router=APIRouter()


@router.post("/lease_finance")
def calculate_lease_full(payload: LeaseInput):
    SF = payload.square_footage
    T = payload.total_term_years
    base_rent = payload.base_rent_psf
    esc_rate = (payload.annual_escalation_rate or Decimal('0')) / 100
    free_months = payload.free_rent_months or 0
    ti_psf = payload.ti_allowance_psf or Decimal('0')
    discount_rate = (payload.discount_rate or Decimal('8')) / 100
    monthly_discount = (1 + discount_rate) ** (Decimal('1')/12) - 1

    # Lists for transparency
    yearly_data = []
    total_gross_rent_pv = Decimal('0')
    total_free_rent_cost_pv = Decimal('0')
    total_ti_cost = ti_psf * SF
    total_commission_pv = Decimal('0')
    total_commission_nominal = Decimal('0')

 
    free_rent_per_month = Decimal('0')
    if free_months > 0:
        first_year_rent_psf = base_rent
        free_rent_per_month = (first_year_rent_psf / 12) * SF

    remaining_free_months = free_months

    for year in range(1, T + 1):
 
        rent_psf = base_rent * ((1 + esc_rate) ** (year - 1))
        gross_annual_rent = rent_psf * SF


        free_rent_this_year = Decimal('0')
        if remaining_free_months > 0:
            months_free_this_year = min(12, remaining_free_months)
            free_rent_this_year = free_rent_per_month * months_free_this_year
            remaining_free_months -= months_free_this_year

        commissionable_rent = gross_annual_rent - free_rent_this_year


        comm_rate = Decimal('0')
        for item in payload.commission_rates:
            if item.year == year:
                comm_rate = item.rate / 100
                break
        commission_this_year = commissionable_rent * comm_rate
        total_commission_nominal += commission_this_year


        monthly_rent = gross_annual_rent / 12
        for m in range(1, 13):
            month_num = (year - 1) * 12 + m
            pv = monthly_rent / ((1 + monthly_discount) ** month_num)
            total_gross_rent_pv += pv


        if free_rent_this_year > 0:
            months_free = min(12, free_months - (free_months - remaining_free_months - months_free_this_year))
            for m in range(1, months_free + 1):
                month_num = (year - 1) * 12 + m
                pv_lost = free_rent_per_month / ((1 + monthly_discount) ** month_num)
                total_free_rent_cost_pv += pv_lost

       
        for m in range(1, 13):
            month_num = (year - 1) * 12 + m + 6  # assume mid-year payment
            pv_comm = commission_this_year / 12 / ((1 + monthly_discount) ** month_num)
            total_commission_pv += pv_comm

        yearly_data.append({
            "year": year,
            "rent_psf": round(rent_psf, 2),
            "gross_rent": round(gross_annual_rent, 2),
            "free_rent_this_year": round(free_rent_this_year, 2),
            "commissionable_rent": round(commissionable_rent, 2),
            "commission_rate_pct": float(comm_rate * 100),
            "commission_amount": round(commission_this_year, 2)
        })

    # Final NER Calculation
    total_concessions_pv = total_free_rent_cost_pv + total_ti_cost + total_commission_pv
    net_cashflow_pv = total_gross_rent_pv - total_concessions_pv
    ner_psf_annual = net_cashflow_pv / (SF * T)

    # Simple commission (if someone still wants old method)
    simple_commission = Decimal('0')
    if payload.simple_commission_total_pct:
        total_contract_value = SF * base_rent * T
        simple_commission = total_contract_value * (payload.simple_commission_total_pct / 100)

    return {
        "net_effective_rent_psf_annual": round(ner_psf_annual, 2),
        "total_commission_advanced": round(total_commission_nominal, 2),
        "total_commission_simple": round(simple_commission, 2),
        "total_ti_cost": round(total_ti_cost, 2),
        "total_free_rent_cost_nominal": round(total_free_rent_cost_pv.quantize(Decimal('0.01'), ROUND_HALF_UP), 2),
        "yearly_breakdown": yearly_data,
        "summary": {
            "total_gross_rent_pv": round(total_gross_rent_pv, 2),
            "total_concessions_pv": round(total_concessions_pv, 2),
            "net_present_value": round(net_cashflow_pv, 2)
        }
    }
