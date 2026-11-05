import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple, Union
import httpx
from dotenv import load_dotenv

from schemas.environmental import (
    Coordinates,
    SensorParameter,
    SensorSummary,
    StationSummary,
    MeasurementRecord,
    StationLatestData,
    HistoricalMeasurement
)

load_dotenv()


class OpenAQService:
    BASE_URL = "https://api.openaq.org/v3"

    def __init__(self, api_key: Optional[str] = None, timeout: float = 20.0):
        self.api_key = api_key or os.getenv("OPENAQ_API_KEY")
        self.timeout = timeout

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def _ensure_api_key(self):
        if not self.api_key:
            raise ValueError(
                "OPENAQ_API_KEY is not configured. Set OPENAQ_API_KEY in the environment."
            )

    def search_locations(
        self,
        query: Optional[str] = None,
        coordinates: Optional[Tuple[float, float]] = None,
        radius_meters: int = 25000,
        iso: Optional[str] = None,
        page: int = 1,
        limit: int = 25,
        return_meta: bool = False
    ) -> Union[List[StationSummary], Dict[str, Any]]:
        """
        Search OpenAQ v3 monitoring locations with pagination and metadata.
        Supports radius search around coordinates or country/bounding query.
        """
        self._ensure_api_key()

        # If textual query provided without coordinates, resolve coordinates for radius search
        if not coordinates and not iso and query:
            q_clean = query.strip()
            if len(q_clean) == 2 and q_clean.isalpha():
                iso = q_clean.upper()
            else:
                try:
                    from services.geospatial_service import GeospatialService
                    geo = GeospatialService()
                    loc = geo.geocode(q_clean)
                    coordinates = (loc.latitude, loc.longitude)
                except Exception:
                    pass

        safe_limit = min(max(int(limit), 1), 100)
        safe_page = max(int(page), 1)
        params: Dict[str, Any] = {"limit": safe_limit, "page": safe_page}
        if coordinates:
            lat, lon = coordinates
            params["coordinates"] = f"{lat},{lon}"
            # OpenAQ v3 API strictly requires radius <= 25000 meters
            params["radius"] = min(int(radius_meters), 25000)
        elif iso:
            params["iso"] = iso

        url = f"{self.BASE_URL}/locations"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url, headers=self._get_headers(), params=params)
            response.raise_for_status()
            data = response.json()

        results = data.get("results", [])
        stations: List[StationSummary] = []

        for item in results:
            # Filter in-memory if user passed query text and no coordinates
            if query and not coordinates:
                name = item.get("name", "").lower()
                locality = (item.get("locality") or "").lower()
                q = query.lower()
                if q not in name and q not in locality:
                    continue

            coords = None
            if item.get("coordinates"):
                c_lat = item["coordinates"].get("latitude")
                c_lon = item["coordinates"].get("longitude")
                if c_lat is not None and c_lon is not None:
                    coords = Coordinates(latitude=c_lat, longitude=c_lon)

            sensors_list: List[SensorSummary] = []
            for s in item.get("sensors", []):
                param_data = s.get("parameter", {})
                sensors_list.append(
                    SensorSummary(
                        id=s.get("id"),
                        parameter=SensorParameter(
                            id=param_data.get("id"),
                            name=param_data.get("name", "unknown"),
                            units=param_data.get("units", ""),
                            display_name=param_data.get("displayName")
                        )
                    )
                )

            stations.append(
                StationSummary(
                    id=item.get("id"),
                    name=item.get("name", f"Station {item.get('id')}"),
                    country=item.get("country", {}).get("name") if isinstance(item.get("country"), dict) else item.get("country"),
                    timezone=item.get("timezone"),
                    coordinates=coords,
                    sensors=sensors_list,
                    is_active=item.get("isMonitor", True)
                )
            )

        meta = data.get("meta", {})
        meta_found = meta.get("found", len(stations))
        has_more = len(results) >= safe_limit
        coverage_note = (
            f"Page {safe_page} returned {len(stations)} station(s) (total found: {meta_found}). "
            f"{'Additional stations exist in other pages; query page=' + str(safe_page + 1) + ' for more.' if has_more else 'All matching stations in this query have been retrieved.'}"
        )

        if return_meta:
            return {
                "page": safe_page,
                "limit": safe_limit,
                "total_found": meta_found,
                "has_more": has_more,
                "coverage_note": coverage_note,
                "stations": stations
            }

        return stations

    def get_station_details(self, location_id: int) -> StationSummary:
        """Fetch station details from OpenAQ v3."""
        self._ensure_api_key()

        url = f"{self.BASE_URL}/locations/{location_id}"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url, headers=self._get_headers())
            response.raise_for_status()
            data = response.json()

        results = data.get("results", [])
        if not results:
            raise LookupError(f"No station found with ID {location_id}")

        item = results[0]
        coords = None
        if item.get("coordinates"):
            c_lat = item["coordinates"].get("latitude")
            c_lon = item["coordinates"].get("longitude")
            if c_lat is not None and c_lon is not None:
                coords = Coordinates(latitude=c_lat, longitude=c_lon)

        sensors: List[SensorSummary] = []
        for s in item.get("sensors", []):
            p = s.get("parameter", {})
            sensors.append(
                SensorSummary(
                    id=s.get("id"),
                    parameter=SensorParameter(
                        id=p.get("id"),
                        name=p.get("name", "unknown"),
                        units=p.get("units", ""),
                        display_name=p.get("displayName")
                    )
                )
            )

        return StationSummary(
            id=item.get("id"),
            name=item.get("name", f"Station {item.get('id')}"),
            country=item.get("country", {}).get("name") if isinstance(item.get("country"), dict) else item.get("country"),
            timezone=item.get("timezone"),
            coordinates=coords,
            sensors=sensors,
            is_active=item.get("isMonitor")
        )

    def get_latest_measurements(self, location_id: int) -> StationLatestData:
        """
        Fetch latest available measurements for a station.
        Determines staleness against current UTC time.
        """
        self._ensure_api_key()

        # First get station details for name and coordinates
        station_info = self.get_station_details(location_id)

        url = f"{self.BASE_URL}/locations/{location_id}/latest"
        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url, headers=self._get_headers(), params={"limit": 100})
            response.raise_for_status()
            data = response.json()

        results = data.get("results", [])
        now_utc = datetime.now(timezone.utc)
        measurements: List[MeasurementRecord] = []
        notes: List[str] = []

        if not results:
            notes.append(f"No recent measurements available for station {location_id}.")

        # Build sensor map to attach accurate parameter name and units
        sensor_map = {s.id: s.parameter for s in station_info.sensors}

        for item in results:
            value = item.get("value")
            if value is None:
                continue

            sensor_id = item.get("sensorsId") or item.get("sensorId") or 0
            mapped_param = sensor_map.get(sensor_id)

            param = item.get("parameter", {})
            param_name = mapped_param.name if mapped_param else (param.get("name") if isinstance(param, dict) else str(param))
            param_units = mapped_param.units if mapped_param else (param.get("units") if isinstance(param, dict) else "")
            if not param_units and item.get("unit"):
                param_units = item.get("unit")

            dt_str = None
            dt_obj = None
            dt_info = item.get("datetime")
            if isinstance(dt_info, dict):
                dt_str = dt_info.get("utc") or dt_info.get("local")
            elif isinstance(dt_info, str):
                dt_str = dt_info
            elif item.get("period"):
                dt_str = item["period"].get("datetimeTo", {}).get("utc")

            if not dt_str:
                dt_str = now_utc.isoformat()

            # Staleness check
            is_stale = False
            stale_hours = None
            try:
                # normalize timestamp
                parsed_dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
                if parsed_dt.tzinfo is None:
                    parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
                diff = now_utc - parsed_dt
                stale_hours = round(diff.total_seconds() / 3600.0, 1)
                if stale_hours > 24.0:
                    is_stale = True
            except Exception:
                pass

            coords = station_info.coordinates
            if item.get("coordinates"):
                c_lat = item["coordinates"].get("latitude")
                c_lon = item["coordinates"].get("longitude")
                if c_lat is not None and c_lon is not None:
                    coords = Coordinates(latitude=c_lat, longitude=c_lon)

            measurements.append(
                MeasurementRecord(
                    sensor_id=item.get("sensorsId") or item.get("sensorId") or 0,
                    parameter_name=param_name or "unknown",
                    value=float(value),
                    units=param_units or "µg/m³",
                    timestamp=dt_str,
                    is_stale=is_stale,
                    stale_hours=stale_hours,
                    coordinates=coords,
                    station_id=location_id,
                    station_name=station_info.name
                )
            )

        if any(m.is_stale for m in measurements):
            stale_count = sum(1 for m in measurements if m.is_stale)
            notes.append(
                f"{stale_count} reading(s) are older than 24 hours and marked as stale."
            )

        return StationLatestData(
            station_id=location_id,
            station_name=station_info.name,
            coordinates=station_info.coordinates,
            timezone=station_info.timezone,
            measurements=measurements,
            retrieved_at=now_utc.isoformat(),
            notes=notes
        )

    def get_sensor_hourly(self, sensor_id: int, limit: int = 24) -> List[HistoricalMeasurement]:
        """Fetch hourly aggregate measurements for a specific sensor."""
        self._ensure_api_key()

        url = f"{self.BASE_URL}/sensors/{sensor_id}/hours"
        params = {"limit": limit, "page": 1}

        with httpx.Client(timeout=self.timeout) as client:
            response = client.get(url, headers=self._get_headers(), params=params)
            response.raise_for_status()
            data = response.json()

        results = data.get("results", [])
        history: List[HistoricalMeasurement] = []

        for item in results:
            period = item.get("period", {})
            param = item.get("parameter", {})
            summary = item.get("summary", {})
            history.append(
                HistoricalMeasurement(
                    sensor_id=sensor_id,
                    parameter_name=param.get("name", "unknown") if isinstance(param, dict) else str(param),
                    units=param.get("units", "") if isinstance(param, dict) else "",
                    period_start=period.get("datetimeFrom", {}).get("utc", ""),
                    period_end=period.get("datetimeTo", {}).get("utc", ""),
                    value_avg=summary.get("avg") or item.get("value"),
                    value_min=summary.get("min"),
                    value_max=summary.get("max"),
                    count=item.get("coverage", {}).get("observedCount")
                )
            )

        return history
