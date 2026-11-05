from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class SensorParameter(BaseModel):
    id: Optional[int] = None
    name: str
    units: str
    display_name: Optional[str] = None


class SensorSummary(BaseModel):
    id: int
    parameter: SensorParameter
    last_value: Optional[float] = None
    last_datetime: Optional[str] = None


class Coordinates(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)


class StationSummary(BaseModel):
    id: int
    name: str
    country: Optional[str] = None
    timezone: Optional[str] = None
    coordinates: Optional[Coordinates] = None
    sensors: List[SensorSummary] = Field(default_factory=list)
    is_active: Optional[bool] = None


class MeasurementRecord(BaseModel):
    sensor_id: int
    parameter_name: str
    value: float
    units: str
    timestamp: str
    is_stale: bool = False
    stale_hours: Optional[float] = None
    coordinates: Optional[Coordinates] = None
    station_id: Optional[int] = None
    station_name: Optional[str] = None


class StationLatestData(BaseModel):
    station_id: int
    station_name: str
    coordinates: Optional[Coordinates] = None
    timezone: Optional[str] = None
    measurements: List[MeasurementRecord] = Field(default_factory=list)
    source_dataset: str = "OpenAQ API v3"
    retrieved_at: str
    notes: List[str] = Field(default_factory=list)


class HistoricalMeasurement(BaseModel):
    sensor_id: int
    parameter_name: str
    units: str
    period_start: str
    period_end: str
    value_avg: Optional[float] = None
    value_min: Optional[float] = None
    value_max: Optional[float] = None
    count: Optional[int] = None

