
from decimal import Decimal, ROUND_HALF_UP
from typing import List
from app.schema.calc import AdvancedCommissionInput, AdvancedCommissionOutput, CommissionYearDetail

def calculate_advanced_commission(inputs: AdvancedCommissionInput) -> AdvancedCommissionOutput:
    """
    Advanced Iterative Commission Calculator
    - Supports variable commission % per year
    - Correctly deducts free rent from commissionable base
    - Supports either flat + escalation or manual per-year rents
    - Returns full audit trail
    """
    SF = inputs.gross_area_sf
    T = inputs.total_term_years
    free_months_total = inputs.free_rent_months


    if inputs.rent_psf_per_year is not None and len(inputs.rent_psf_per_year) == T:
        rent_psf_per_year = [Decimal(str(r)) for r in inputs.rent_psf_per_year]
    elif inputs.base_rent_psf_year1 is not None:
        E = (inputs.annual_escalation_rate or Decimal('0')) / 100
        base = Decimal(str(inputs.base_rent_psf_year1))
        rent_psf_per_year = [
            base * (Decimal('1') + E) ** (year - 1)
            for year in range(1, T + 1)
        ]
    else:
        raise ValueError("Must provide either base_rent_psf_year1 + escalation or rent_psf_per_year list")


    commission_rate_map = {cr.year: Decimal(str(cr.rate)) for cr in inputs.commission_rates}

 
    remaining_free_months = free_months_total
    annual_breakdown: List[CommissionYearDetail] = []
    total_commission = Decimal('0')
    total_commissionable = Decimal('0')
    total_free_rent_value = Decimal('0')

    monthly_rent_year1 = rent_psf_per_year[0] * SF / 12

    for year in range(1, T + 1):
        face_rent_psf = rent_psf_per_year[year - 1]
        gross_annual_rent = face_rent_psf * SF


        free_rent_this_year = Decimal('0')
        if remaining_free_months > 0:
            months_in_year = Decimal('12')
            free_this_year = min(remaining_free_months, months_in_year)
            free_rent_this_year = monthly_rent_year1 * free_this_year 
            remaining_free_months -= free_this_year
            total_free_rent_value += free_rent_this_year

        commissionable_rent = gross_annual_rent - free_rent_this_year
        if commissionable_rent < 0:
            commissionable_rent = Decimal('0')  

        rate_pct = commission_rate_map[year]
        commission_amount = (commissionable_rent * rate_pct / 100).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        annual_breakdown.append(CommissionYearDetail(
            year=year,
            face_rent_psf=face_rent_psf.quantize(Decimal('0.0001')),
            gross_annual_rent=gross_annual_rent.quantize(Decimal('0.01')),
            free_rent_this_year=free_rent_this_year.quantize(Decimal('0.01')),
            commissionable_rent=commissionable_rent.quantize(Decimal('0.01')),
            commission_rate_pct=rate_pct.quantize(Decimal('0.00')),
            commission_amount=commission_amount
        ))

        total_commission += commission_amount
        total_commissionable += commissionable_rent

    return AdvancedCommissionOutput(
        total_commission_due=total_commission.quantize(Decimal('0.01')),
        total_commissionable_rent=total_commissionable.quantize(Decimal('0.01')),
        total_free_rent_value=total_free_rent_value.quantize(Decimal('0.01')),
        annual_breakdown=annual_breakdown
    )

import math
from fastapi import HTTPException
from app.schema.calc import LeaseFinanceInput


def calculate_npv_rent_stream(
    face_rent_psf: float,
    gross_area_sf: float,
    total_term_years: float,
    annual_escalation_rate: float,
    discount_rate: float
) -> float:
    """
    Calculate the NPV of the rent stream with annual escalations.
    Discounts monthly cash flows back to present value.
    """
    monthly_discount_rate = discount_rate / 100 / 12
    total_months = int(total_term_years * 12)
    npv_rent = 0.0
    
    for month in range(1, total_months + 1):

        year = (month - 1) // 12
        
 
        annual_rent_psf = face_rent_psf * math.pow(1 + annual_escalation_rate / 100, year)
        monthly_rent_psf = annual_rent_psf / 12

        monthly_rent_total = monthly_rent_psf * gross_area_sf
        
        # Discount back to present value
        pv_factor = 1 / math.pow(1 + monthly_discount_rate, month)
        npv_rent += monthly_rent_total * pv_factor
    
    return npv_rent


def calculate_npv_free_rent(
    face_rent_psf: float,
    gross_area_sf: float,
    free_rent_months: float,
    discount_rate: float
) -> float:
    """
    Calculate the NPV of free rent concession.
    Assumes free rent occurs at the beginning of the lease.
    """
    monthly_discount_rate = discount_rate / 100 / 12
    monthly_rent = (face_rent_psf / 12) * gross_area_sf
    npv_free_rent = 0.0
    
    for month in range(1, int(free_rent_months) + 1):
        pv_factor = 1 / math.pow(1 + monthly_discount_rate, month)
        npv_free_rent += monthly_rent * pv_factor
    
    return npv_free_rent


def calculate_npv_ti_allowance(
    ti_allowance_psf: float,
    gross_area_sf: float
) -> float:
    """
    Calculate TI allowance (assumed paid upfront, so no discounting needed).
    """
    return ti_allowance_psf * gross_area_sf


def calculate_total_commission_for_ner(
    face_rent_psf: float,
    gross_area_sf: float,
    total_term_years: int,
    annual_escalation_rate: float,
    commission_rate_per_year: float
) -> float:
    """
    Calculate total broker commission (NON-DISCOUNTED) for NER calculation.
    Commission is X% per year of the gross annual rent for that year.
    This is NOT an NPV calculation - it's the actual cash amount paid.
    """
    total_commission = 0.0
    
    for year in range(total_term_years):
        # Calculate gross rent for this year with escalation
        annual_rent_psf = face_rent_psf * math.pow(1 + annual_escalation_rate / 100, year)
        gross_rent_year = annual_rent_psf * gross_area_sf
        
        # Commission for this year (e.g., 2.5% of that year's rent)
        commission_year = gross_rent_year * (commission_rate_per_year / 100)
        total_commission += commission_year
    
    return total_commission


def calculate_ner(inputs: LeaseFinanceInput) -> dict:
    """
    Calculate Net Effective Rent using NPV methodology.
    
    IMPORTANT: Per the specification, commission is calculated as total cash outflow,
    NOT discounted. The formula is: Commission = Sum of (Annual Rent × Commission Rate) 
    for each year.
    """
    # Validate required inputs
    required_fields = [
        'face_rent_psf', 'annual_escalation_rate', 'discount_rate'
    ]
    for field in required_fields:
        if getattr(inputs, field) is None:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required field for NER calculation: {field}"
            )
    
    # Default values for optional fields
    free_rent_months = inputs.free_rent_months or 0
    ti_allowance_psf = inputs.ti_allowance_psf or 0
    commission_rate_per_year = inputs.commission_rate_per_year or 0
    
    # Calculate NPV of rent stream (income)
    npv_rent = calculate_npv_rent_stream(
        inputs.face_rent_psf,
        inputs.gross_area_sf,
        inputs.total_term_years,
        inputs.annual_escalation_rate,
        inputs.discount_rate
    )
    
    # Calculate NPV of free rent (cost)
    npv_free_rent = calculate_npv_free_rent(
        inputs.face_rent_psf,
        inputs.gross_area_sf,
        free_rent_months,
        inputs.discount_rate
    )
    
    # TI Allowance (upfront cost, no discounting)
    ti_cost = calculate_npv_ti_allowance(
        ti_allowance_psf,
        inputs.gross_area_sf
    )
    
    # Commission calculation - TOTAL CASH OUTFLOW (not NPV)
    # This is the sum of commission payments across all years
    total_commission = calculate_total_commission_for_ner(
        inputs.face_rent_psf,
        inputs.gross_area_sf,
        int(inputs.total_term_years),
        inputs.annual_escalation_rate,
        commission_rate_per_year
    )
    
    # Total concessions (all costs)
    total_concessions = npv_free_rent + ti_cost + total_commission
    
    # Net cash flow
    net_cash_flow = npv_rent - total_concessions
    
    # NER per square foot per year
    ner_psf_annual = net_cash_flow / (inputs.gross_area_sf * inputs.total_term_years)
    
    return {
        'ner_psf_annual': round(ner_psf_annual, 2),
        'total_cash_outflow_concessions': round(total_concessions, 2),
        'calculation_details': {
            'npv_rent_income': round(npv_rent, 2),
            'npv_free_rent': round(npv_free_rent, 2),
            'ti_allowance': round(ti_cost, 2),
            'total_commission': round(total_commission, 2),
            'net_cash_flow': round(net_cash_flow, 2)
        }
    }


def calculate_commission_simple(inputs: LeaseFinanceInput) -> dict:
    """
    Calculate simple commission based on total contract value.
    This is separate from the NER commission calculation.
    """
    if inputs.commission_rate_total is None or inputs.face_rent_psf is None:
        raise HTTPException(
            status_code=400,
            detail="Missing required fields for commission calculation"
        )
    
    # Total contract value (gross) - no escalations considered here
    total_contract_value = (
        inputs.gross_area_sf * 
        inputs.face_rent_psf * 
        inputs.total_term_years
    )
    
    # Total commission as percentage of total contract
    total_commission = total_contract_value * (inputs.commission_rate_total / 100)
    
    return {
        'total_commission_due': round(total_commission, 2),
        'calculation_details': {
            'total_contract_value': round(total_contract_value, 2),
            'commission_rate': inputs.commission_rate_total
        }
    }


