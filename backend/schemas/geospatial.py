from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class GeocodedLocation(BaseModel):
    query: str
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    display_name: str
    bounding_box: Optional[List[float]] = None
    osm_type: Optional[str] = None
    confidence: Optional[float] = None
    source: str = "OpenStreetMap Nominatim"


class EmissionSource(BaseModel):
    id: str
    name: str
    source_type: str  # industrial, power, manufacturing, transport_hub
    latitude: float
    longitude: float
    distance_km: float
    source_dataset: str = "OpenStreetMap Overpass"


class InvestigationBuffer(BaseModel):
    center_latitude: float
    center_longitude: float
    radius_km: float
    area_km2: float
    geometry_geojson: Dict[str, Any]
    disclaimer: str = (
        "Circular buffer is an estimated spatial investigation area, NOT a "
        "scientifically established atmospheric dispersion plume or boundary."
    )
    source_dataset: str = "Shapely Geodesic Buffer"


class GeoJSONFeature(BaseModel):
    type: Literal["Feature"] = "Feature"
    geometry: Dict[str, Any]
    properties: Dict[str, Any] = Field(default_factory=dict)


class GeoJSONFeatureCollection(BaseModel):
    type: Literal["FeatureCollection"] = "FeatureCollection"
    features: List[GeoJSONFeature] = Field(default_factory=list)

