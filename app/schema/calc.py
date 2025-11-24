# from pydantic import BaseModel
# # Request model for calculations
# class CalculatorInput(BaseModel):
#     rent: float
#     commission_rate: float  # percentage, e.g., 5 for 5%
#     concessions: float = 0  # optional concessions

# # Response model
# class CalculatorOutput(BaseModel):
#     commission_amount: float
#     net_effective_rent: float