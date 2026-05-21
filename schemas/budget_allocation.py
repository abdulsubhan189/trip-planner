from pydantic import BaseModel
from typing import Dict

class BudgetAllocation(BaseModel):
    total_budget: float
    hotel: float = 0.0
    flights: float = 0.0
    food: float = 0.0
    transport: float = 0.0
    activities: float = 0.0
    emergency_reserve: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        return self.dict()