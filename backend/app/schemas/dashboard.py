from pydantic import BaseModel


class DashboardSummary(BaseModel):
    total_products: int = 0
    analyzed_products: int = 0
    total_landings: int = 0
    published_products: int = 0
    credits_remaining: float = 0
