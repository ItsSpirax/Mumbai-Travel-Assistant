from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from functools import lru_cache, partial
from typing import Any, Dict, List, Optional

from FlightRadar24 import FlightRadar24API

from app import mcp


MAX_LIMIT = 100


@lru_cache(maxsize=1)
def _get_api() -> FlightRadar24API:
    return FlightRadar24API()


@lru_cache(maxsize=1)
def _get_cached_zones() -> Dict[str, Any]:
    api = _get_api()
    return api.get_zones()


def _drop_none(mapping: Dict[str, Any]) -> Dict[str, Any]:
    return {
        key: value for key, value in mapping.items() if value not in (None, "", [], {})
    }


def _ts_to_iso(timestamp: Optional[float]) -> Optional[str]:
    if not timestamp:
        return None
    try:
        return datetime.fromtimestamp(float(timestamp), tz=timezone.utc).isoformat()
    except (TypeError, ValueError):
        return None


def _normalize_limit(limit: int) -> int:
    if limit <= 0:
        raise ValueError("limit must be greater than zero")
    return min(limit, MAX_LIMIT)


def _normalize_offset(offset: int) -> int:
    if offset < 0:
        raise ValueError("offset cannot be negative")
    return offset


async def _get_flights_async(**kwargs: Any) -> List[Any]:
    api = _get_api()
    loop = asyncio.get_running_loop()
    fetch = partial(api.get_flights, **kwargs)
    return await loop.run_in_executor(None, fetch)


async def _get_flight_details_async(flight: Any) -> Any:
    api = _get_api()
    loop = asyncio.get_running_loop()
    fetch = partial(api.get_flight_details, flight)
    return await loop.run_in_executor(None, fetch)


def _sanitize_value(value: Any, include_coordinates: bool) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    if isinstance(value, dict):
        sanitized = {
            key: _sanitize_value(val, include_coordinates)
            for key, val in value.items()
            if val is not None
        }
        return {key: val for key, val in sanitized.items() if val is not None}
    if isinstance(value, list):
        sanitized_list = [
            _sanitize_value(item, include_coordinates)
            for item in value
            if item is not None
        ]
        return [item for item in sanitized_list if item is not None]
    if hasattr(value, "__dict__"):
        data: Dict[str, Any] = {}
        for key, val in value.__dict__.items():
            if key.startswith("_"):
                continue
            if not include_coordinates and key in {"latitude", "longitude"}:
                continue
            sanitized = _sanitize_value(val, include_coordinates)
            if sanitized is not None:
                data[key] = sanitized
        return data if data else None
    return str(value)


def _serialize_airport_reference(
    flight: Any, prefix: str, include_coordinates: bool
) -> Optional[Dict[str, Any]]:
    airport_obj = getattr(flight, f"airport_{prefix}", None)
    data = _sanitize_value(airport_obj, include_coordinates)
    fallback = _drop_none(
        {
            "name": getattr(flight, f"{prefix}_airport_name", None),
            "iata": getattr(flight, f"{prefix}_airport_iata", None),
            "icao": getattr(flight, f"{prefix}_airport_icao", None),
            "country": getattr(flight, f"{prefix}_airport_country", None),
            "city": getattr(flight, f"{prefix}_airport_city", None),
        }
    )
    if data and isinstance(data, dict):
        if fallback:
            data.update({key: val for key, val in fallback.items() if val is not None})
        return data
    return fallback or None


def _serialize_time_block(time_block: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(time_block, dict):
        return None
    serialized: Dict[str, Any] = {}
    for key, value in time_block.items():
        if isinstance(value, (int, float)):
            converted = _ts_to_iso(value)
        elif isinstance(value, dict):
            converted = {
                inner_key: (
                    _ts_to_iso(inner_val)
                    if isinstance(inner_val, (int, float))
                    else inner_val
                )
                for inner_key, inner_val in value.items()
                if inner_val is not None
            }
        else:
            converted = value
        if converted not in (None, {}):
            serialized[key] = converted
    return serialized or None


def _serialize_flight(
    flight: Any,
    include_coordinates: bool,
    include_trail: bool,
) -> Dict[str, Any]:
    position = _drop_none(
        {
            "latitude": (
                getattr(flight, "latitude", None) if include_coordinates else None
            ),
            "longitude": (
                getattr(flight, "longitude", None) if include_coordinates else None
            ),
            "altitude_ft": getattr(flight, "altitude", None),
            "ground_speed_kts": getattr(flight, "ground_speed", None),
            "vertical_speed_fpm": getattr(flight, "vertical_speed", None),
            "heading_deg": getattr(flight, "heading", None),
        }
    )

    airline = _drop_none(
        {
            "icao": getattr(flight, "airline_icao", None),
            "iata": getattr(flight, "airline_iata", None),
            "name": getattr(flight, "airline_name", None),
        }
    )

    aircraft = _drop_none(
        {
            "registration": getattr(flight, "registration", None),
            "icao_type": getattr(flight, "aircraft_code", None),
            "model": getattr(flight, "aircraft_type", None),
        }
    )

    origin = _serialize_airport_reference(flight, "origin", include_coordinates)
    destination = _serialize_airport_reference(
        flight, "destination", include_coordinates
    )

    time_info = _serialize_time_block(getattr(flight, "time", None))

    result: Dict[str, Any] = _drop_none(
        {
            "flight_id": getattr(flight, "id", None),
            "callsign": getattr(flight, "callsign", None),
            "flight_number": getattr(flight, "number", None),
            "squawk": getattr(flight, "squawk", None),
            "on_ground": getattr(flight, "on_ground", None),
            "position": position if position else None,
            "airline": airline if airline else None,
            "aircraft": aircraft if aircraft else None,
            "origin": origin,
            "destination": destination,
            "time": time_info,
            "status_text": getattr(flight, "status_text", None),
        }
    )

    if include_trail:
        trail = getattr(flight, "trail", None)
        if isinstance(trail, list) and trail:
            result["trail"] = [
                _drop_none(
                    {
                        "latitude": point.get("lat") if include_coordinates else None,
                        "longitude": point.get("lng") if include_coordinates else None,
                        "altitude_ft": point.get("altitude"),
                        "timestamp": _ts_to_iso(point.get("timestamp")),
                    }
                )
                for point in trail
                if isinstance(point, dict)
            ]
            result["trail"] = [item for item in result["trail"] if item]
            if not result["trail"]:
                result.pop("trail", None)

    return result


def _resolve_bounds(
    bounds: Optional[str],
    zone: Optional[str],
    center_lat: Optional[float],
    center_lon: Optional[float],
    radius_m: Optional[int],
) -> Dict[str, Any]:
    api = _get_api()
    resolved: Optional[str] = None
    notes: List[str] = []

    if bounds:
        resolved = bounds
    elif center_lat is not None and center_lon is not None:
        try:
            radius = radius_m if radius_m and radius_m > 0 else 2000
            resolved = api.get_bounds_by_point(center_lat, center_lon, radius)
            notes.append("bounds derived via center point")
        except Exception as exc:
            notes.append(f"failed to derive bounds from point: {exc}")
    elif zone:
        zones = _get_cached_zones()
        zone_key = zone.lower()
        match = None
        for key, value in zones.items():
            if key.lower() == zone_key:
                match = value
                break
        if match is None:
            notes.append(f"zone '{zone}' not recognised; fallback to global scope")
        else:
            try:
                resolved = api.get_bounds(match)
                notes.append(f"bounds derived from zone '{zone}'")
            except Exception as exc:
                notes.append(f"failed to derive bounds from zone '{zone}': {exc}")

    return {
        "bounds": resolved,
        "notes": notes,
    }


@mcp.tool(name="flight_tracker_lookup")
async def flight_tracker_lookup(
    airline: Optional[str] = None,
    aircraft_type: Optional[str] = None,
    bounds: Optional[str] = None,
    zone: Optional[str] = None,
    center_lat: Optional[float] = None,
    center_lon: Optional[float] = None,
    radius_m: int = 2000,
    limit: int = 25,
    offset: int = 0,
    include_trail: bool = False,
    include_details: bool = False,
    include_coordinates: bool = True,
) -> Dict[str, Any]:
    """
    Retrieve live flight data using FlightRadar24's public API wrapper.

    **TOOL SIGNATURE:**
    ```python
    flight_tracker_lookup(
        airline: Optional[str] = None,           # ICAO airline code
        aircraft_type: Optional[str] = None,     # ICAO aircraft type
        bounds: Optional[str] = None,            # "lat1,lat2,lat3,lat4"
        zone: Optional[str] = None,              # FlightRadar24 zone name
        center_lat: Optional[float] = None,      # Center point latitude
        center_lon: Optional[float] = None,      # Center point longitude
        radius_m: int = 2000,                    # Radius in meters
        limit: int = 25,                         # Max 100
        offset: int = 0,                         # Pagination offset
        include_trail: bool = False,             # Include track history
        include_details: bool = False,           # Fetch detailed data
        include_coordinates: bool = True         # Include lat/lon in output
    ) -> Dict[str, Any]
    ```

    **PARAMETERS:**
    - airline (str, optional): ICAO airline code filter (e.g., "UAE" for Emirates)
    - aircraft_type (str, optional): ICAO aircraft type (e.g., "B77W", "A388")
    - bounds (str, optional): Custom bounds "lat1,lat2,lat3,lat4"
    - zone (str, optional): Named zone (e.g., "asia", "northamerica", "europe")
    - center_lat (float, optional): Latitude for point-based search
    - center_lon (float, optional): Longitude for point-based search
    - radius_m (int): Radius in meters for point search (default 2000)
    - limit (int): Max flights to return (max 100, must be > 0)
    - offset (int): Skip N flights for pagination (must be >= 0)
    - include_trail (bool): Include recent position history
    - include_details (bool): Fetch full flight details (extra API calls)
    - include_coordinates (bool): Include lat/lon in output

    **RETURNS:**
    Dict[str, Any]:
    {
        "metadata": {
            "retrieved_at": str,      # ISO 8601 UTC
            "total_available": int,
            "limit": int,
            "offset": int,
            "returned": int
        },
        "filters": {
            "airline": Optional[str],
            "aircraft_type": Optional[str],
            "bounds": Optional[str],
            "zone": Optional[str],
            "center_lat": Optional[float],
            "center_lon": Optional[float],
            "radius_m": Optional[int]
        },
        "notes": List[str],  # Bounds resolution notes
        "flights": [
            {
                "flight_id": str,
                "callsign": str,
                "flight_number": str,
                "squawk": str,
                "on_ground": bool,
                "position": {
                    "latitude": Optional[float],
                    "longitude": Optional[float],
                    "altitude_ft": int,
                    "ground_speed_kts": int,
                    "vertical_speed_fpm": int,
                    "heading_deg": int
                },
                "airline": {
                    "icao": str,
                    "iata": str,
                    "name": str
                },
                "aircraft": {
                    "registration": str,
                    "icao_type": str,
                    "model": str
                },
                "origin": {
                    "name": str,
                    "iata": str,
                    "icao": str,
                    "city": str,
                    "country": str,
                    "latitude": Optional[float],
                    "longitude": Optional[float]
                },
                "destination": {
                    "name": str,
                    "iata": str,
                    "icao": str,
                    "city": str,
                    "country": str,
                    "latitude": Optional[float],
                    "longitude": Optional[float]
                },
                "time": {
                    "scheduled": {"departure": str, "arrival": str},
                    "estimated": {"departure": str, "arrival": str}
                },
                "status_text": str,
                "trail": Optional[List[{
                    "latitude": float,
                    "longitude": float,
                    "altitude_ft": int,
                    "timestamp": str
                }]],
                "details": Optional[Dict]  # If include_details=True
            }
        ]
    }

    **USAGE EXAMPLES:**

    Example 1 - Flights around Mumbai airport:
    ```python
    result = await flight_tracker_lookup(
        center_lat=19.0896,
        center_lon=72.8656,
        radius_m=50000,
        limit=10
    )
    # Returns up to 10 flights within 50km of Mumbai
    ```

    Example 2 - Specific airline flights:
    ```python
    result = await flight_tracker_lookup(
        airline="UAE",  # Emirates
        limit=20
    )
    # Returns Emirates flights
    ```

    Example 3 - Aircraft type in zone:
    ```python
    result = await flight_tracker_lookup(
        aircraft_type="A388",  # A380-800
        zone="asia",
        limit=15
    )
    # All A380s in Asia region
    ```

    Example 4 - Custom bounds (Mumbai to Delhi corridor):
    ```python
    result = await flight_tracker_lookup(
        bounds="18.5,28.5,72.0,77.5",
        limit=50
    )
    # Flights in rectangular area
    ```

    Example 5 - Minimal data for performance:
    ```python
    result = await flight_tracker_lookup(
        zone="asia",
        limit=100,
        include_coordinates=False,
        include_trail=False,
        include_details=False
    )
    # Fast query with minimal data
    ```

    **COMMON ICAO CODES:**
    Airlines: UAE (Emirates), AIC (Air India), UAE (Qatar), DLH (Lufthansa)
    Aircraft: B77W (777-300ER), A388 (A380-800), B789 (787-9), A21N (A321neo)

    **GEOGRAPHIC ZONES:**
    - asia, europe, northamerica, southamerica, africa, oceania

    **ERROR CONDITIONS:**
    - ValueError: limit <= 0 or offset < 0
    - Exception: Network error or API failure (returns error dict)
    - Empty results: "flights": [] with metadata showing 0 available
    """

    limit = _normalize_limit(limit)
    offset = _normalize_offset(offset)

    bounds_payload = _resolve_bounds(bounds, zone, center_lat, center_lon, radius_m)
    effective_bounds = bounds_payload["bounds"]

    kwargs: Dict[str, Any] = {}
    if effective_bounds:
        kwargs["bounds"] = effective_bounds
    if airline:
        kwargs["airline"] = airline
    if aircraft_type:
        kwargs["aircraft_type"] = aircraft_type

    try:
        flights = await _get_flights_async(**kwargs)
    except Exception as exc:
        return {
            "error": "Unable to fetch live flights",
            "details": str(exc),
            "filters": _drop_none(
                {
                    "airline": airline,
                    "aircraft_type": aircraft_type,
                    "bounds": effective_bounds,
                    "zone": zone,
                }
            ),
        }

    flight_list = list(flights) if isinstance(flights, (list, tuple)) else []
    total_available = len(flight_list)

    sliced = flight_list[offset : offset + limit]

    details_payloads: List[Any] = []
    if include_details and sliced:
        detail_tasks = [_get_flight_details_async(flight) for flight in sliced]
        detail_results = await asyncio.gather(*detail_tasks, return_exceptions=True)
        for flight, detail in zip(sliced, detail_results):
            if isinstance(detail, Exception):
                details_payloads.append({"error": str(detail)})
                continue
            try:
                flight.set_flight_details(detail)
            except AttributeError:
                pass
            details_payloads.append(_sanitize_value(detail, include_coordinates))
    else:
        details_payloads = [None] * len(sliced)

    serialized_flights: List[Dict[str, Any]] = []
    for idx, flight in enumerate(sliced):
        flight_payload = _serialize_flight(flight, include_coordinates, include_trail)
        detail_payload = details_payloads[idx]
        if include_details and detail_payload:
            flight_payload["details"] = detail_payload
        serialized_flights.append(flight_payload)

    metadata = {
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "total_available": total_available,
        "limit": limit,
        "offset": offset,
        "returned": len(serialized_flights),
    }

    response: Dict[str, Any] = {
        "metadata": metadata,
        "filters": _drop_none(
            {
                "airline": airline,
                "aircraft_type": aircraft_type,
                "bounds": effective_bounds,
                "zone": zone,
                "center_lat": center_lat,
                "center_lon": center_lon,
                "radius_m": (
                    radius_m
                    if center_lat is not None and center_lon is not None
                    else None
                ),
            }
        ),
        "notes": bounds_payload["notes"],
        "flights": serialized_flights,
    }

    return response
