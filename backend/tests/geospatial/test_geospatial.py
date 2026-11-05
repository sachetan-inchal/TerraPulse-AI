import pytest
from services.geospatial_service import GeospatialService


def test_coordinate_validation():
    service = GeospatialService()

    # Valid
    valid, err = service.validate_coordinates(12.97, 77.59)
    assert valid is True
    assert err is None

    # Invalid Lat
    valid, err = service.validate_coordinates(125.0, 77.59)
    assert valid is False
    assert "Latitude 125.0 is out of bounds" in err

    # Invalid Lon
    valid, err = service.validate_coordinates(12.97, 210.0)
    assert valid is False
    assert "Longitude 210.0 is out of bounds" in err


def test_investigation_buffer_area():
    service = GeospatialService()
    buf = service.create_investigation_buffer(12.97, 77.59, radius_km=2.0)
    # Area = pi * r^2 = ~12.57 km2
    assert abs(buf.area_km2 - 12.57) < 0.1
    assert "NOT a scientifically calculated atmospheric dispersion" in buf.disclaimer


def test_haversine_distance():
    service = GeospatialService()
    # Approx distance between Delhi (28.6139, 77.2090) and Kanpur (26.4499, 80.3319) is ~380-420 km
    dist = service.haversine_distance(28.6139, 77.2090, 26.4499, 80.3319)
    assert 380.0 <= dist <= 420.0

