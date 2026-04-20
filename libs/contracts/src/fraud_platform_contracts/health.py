from datetime import datetime

from pydantic import BaseModel, Field


class DependencyStatus(BaseModel):
    name: str
    healthy: bool
    host: str
    port: int
    detail: str | None = None


class HealthResponse(BaseModel):
    service: str
    version: str = Field(default="0.1.0")
    status: str
    checked_at: datetime
    dependencies: list[DependencyStatus] = Field(default_factory=list)
