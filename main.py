# Mifos Intelligent Loan Simulator
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional

app = FastAPI()

# Input data model
class LoanRequest(BaseModel):
    principal: Decimal
    interest_rate: Decimal
    term_period: int
    prepayment_amount: Optional[Decimal] = Decimal('0')
    prepayment_month: Optional[int] = None
    moratorium_period: Optional[int] = 0  # Months with 0 principal payment

# Schedule entry model
class ScheduleEntry(BaseModel):
    month: int
    opening_balance: Decimal
    principal_paid: Decimal
    interest_paid: Decimal
    extra_payment: Decimal
    closing_balance: Decimal

# Calculation engine
def generate_schedule(data: LoanRequest):
    P = data.principal
    annual_rate = data.interest_rate / 100
    monthly_rate = annual_rate / 12
    n = data.term_period
    m_period = data.moratorium_period

    # Calculate EMI for the periods after moratorium
    if monthly_rate > 0:
        actual_repayment_months = n - m_period
        emi = (P * monthly_rate * (1 + monthly_rate)**actual_repayment_months) / ((1 + monthly_rate)**actual_repayment_months - 1)
    else:
        emi = P / (n - m_period)

    schedule = []
    current_balance = P

    for month in range(1, n + 1):
        if current_balance <= 0:
            break
            
        opening_balance = current_balance
        interest_component = current_balance * monthly_rate
        
        # Moratorium logic: 0 principal during holiday
        if month <= m_period:
            principal_component = Decimal('0')
        else:
            principal_component = emi - interest_component
        
        # Extra payment logic
        extra = Decimal('0')
        if data.prepayment_month == month:
            extra = data.prepayment_amount

        total_principal = principal_component + extra
        
        # Balance check
        if total_principal > current_balance:
            total_principal = current_balance
            extra = total_principal - principal_component if total_principal > principal_component else Decimal('0')

        current_balance -= total_principal

        schedule.append(
            ScheduleEntry(
                month=month, opening_balance=opening_balance.quantize(Decimal('0.01')),
                principal_paid=principal_component.quantize(Decimal('0.01')),
                interest_paid=interest_component.quantize(Decimal('0.01')),
                extra_payment=extra.quantize(Decimal('0.01')),
                closing_balance=current_balance.quantize(Decimal('0.01'))
            )
        )
    return schedule

# API Endpoint
@app.post("/simulate")
def simulate(data: LoanRequest):
    schedule = generate_schedule(data)
    
    return {
        "summary": {
            "total_principal": data.principal,
            "total_interest": sum(item.interest_paid for item in schedule),
            "final_term": len(schedule)
        },
        "schedule": schedule
    }
@app.get("/")
def health_check():
    # Simple endpoint to verify the service is running
    return {"status": "Simulator is online", "version": "1.0.0"}