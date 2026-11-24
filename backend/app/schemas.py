from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ReportResponse(BaseModel):
    id: int
    input_channel: Literal["SMARTPHONE", "USSD", "IVR"]
    image_url: str | None
    image_available: bool
    ai_status: str
    predicted_problem: str | None
    reported_problem: str | None
    problem: str | None
    severity: str
    confidence: float | None
    latitude: float | None
    longitude: float | None
    area: str
    timestamp: str
    weather_status: str
    temperature: float | None
    humidity: float | None
    weather_timestamp: str | None
    risk_level: str
    risk_score: int
    risk_reasons: list[str]
    alert_generated: bool
    is_sample: bool

    model_config = ConfigDict(from_attributes=True)


class AlertResponse(BaseModel):
    id: int
    report_id: int
    problem: str
    risk_level: str
    area: str
    reason: str
    guidance: str
    created_at: str
    delivery_channels: list[str]
    delivery_status: str


class RiskResponse(BaseModel):
    area: str
    problem: str | None
    risk_level: str
    risk_score: int
    reasons: list[str]
    report_count: int
    window_days: int
    weather_status: str
    temperature: float | None
    humidity: float | None
    calculated_at: str
    prototype_notice: str


class USSDRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    text: str = Field(default="", max_length=100)
    area: str | None = Field(default=None, max_length=100)


class IVRRequest(BaseModel):
    session_id: str = Field(min_length=1, max_length=128)
    digit: str | None = Field(default=None, pattern=r"^[0-9]$")
    area: str | None = Field(default=None, max_length=100)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
