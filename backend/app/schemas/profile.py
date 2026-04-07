from pydantic import BaseModel, Field


class ProfileIn(BaseModel):
    monthly_income: float = Field(gt=0)
    savings: float = Field(ge=0)
    investment_goal: str = Field(min_length=2, max_length=200)
    risk_tolerance: int = Field(ge=1, le=10)
