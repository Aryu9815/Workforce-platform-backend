from pydantic import BaseModel
from typing import Dict, Any


class DashboardOverviewResponse(BaseModel):
    hr: Dict[str, Any]
    attendance: Dict[str, Any]
    leave: Dict[str, Any]
    project: Dict[str, Any]
    task: Dict[str, Any]
    finance: Dict[str, Any]