# from fastapi import FastAPI

# from app.schema.calc import CalculatorInput, CalculatorOutput


# app = FastAPI(title="Rent & Commission Calculator")



# @app.post("/calculate", response_model=CalculatorOutput)
# async def calculate(data: CalculatorInput):
#     """
#     Calculate commission and net effective rent.
#     """
#     commission_amount = data.rent * (data.commission_rate / 100)
#     net_effective_rent = data.rent - commission_amount - data.concessions

#     return CalculatorOutput(
#         commission_amount=round(commission_amount, 2),
#         net_effective_rent=round(net_effective_rent, 2)
#     )


