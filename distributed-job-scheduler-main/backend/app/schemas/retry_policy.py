from typing import Literal
from pydantic import BaseModel, Field


class RetryPolicyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    strategy: Literal["fixed", "linear", "exponential"] = "exponential"
    max_attempts: int = Field(default=3, ge=1, le=20)
    initial_delay_seconds: int = Field(default=5, ge=1, le=86400)
    backoff_multiplier: float = Field(default=2.0, ge=1.0, le=10.0)


class RetryPolicyCreate(RetryPolicyBase):
    pass


class RetryPolicyUpdate(BaseModel):
    name: str | None = None
    strategy: Literal["fixed", "linear", "exponential"] | None = None
    max_attempts: int | None = Field(default=None, ge=1, le=20)
    initial_delay_seconds: int | None = Field(default=None, ge=1, le=86400)
    backoff_multiplier: float | None = Field(default=None, ge=1.0, le=10.0)


class RetryPolicyResponse(RetryPolicyBase):
    id: str

    class Config:
        from_attributes = True
