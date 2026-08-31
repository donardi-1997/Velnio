from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime


class AnalysisResponse(BaseModel):
    id: UUID
    product_id: UUID
    overall_score: float
    demand_score: float
    visual_score: float
    problem_score: float
    margin_score: float
    saturation_score: float
    ad_potential_score: float
    impulse_score: float
    return_risk_score: float
    summary: str
    strengths: List[str]
    risks: List[str]
    recommended_price_min: Optional[float] = None
    recommended_price_max: Optional[float] = None
    generated_at: datetime

    class Config:
        from_attributes = True
