from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from functools import lru_cache, partial
from typing import Any, Dict, List, Literal, Optional, Union

from FlightRadar24 import FlightRadar24API
from pydantic import BaseModel, Field

from app import mcp


Direction = Literal["both", "arrivals", "departures"]

MAX_LIMIT = 50


class Location(BaseModel):
    """Represents a geographical airport location."""

    name: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    terminal: Optional[str] = None
    gate: Optional[str] = None
    baggage: Optional[str] = None
    iata: Optional[str] = Field(None, description="3-letter IATA airport code.")
    icao: Optional[str] = Field(None, description="4-letter ICAO airport code.")
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class Aircraft(BaseModel):
    """Represents details of the aircraft for a specific flight."""

    model: Optional[str] = None
    registration: Optional[str] = None
    hex: Optional[str] = Field(
        None, description="Aircraft's ICAO 24-bit address (hex)."
    )


class Flight(BaseModel):
    """Represents a single flight, either arriving or departing."""

    airline: Optional[str] = None
    flight_number: Optional[str] = None
    callsign: Optional[str] = None
    status: Optional[str] = Field(
        None, description="Human-readable flight status (e.g., 'Landed', 'En-route')."
    )
    scheduled_time: Optional[str] = Field(
        None, description="Scheduled time in ISO 8601 UTC format."
    )
    estimated_time: Optional[str] = Field(
        None, description="Estimated time in ISO 8601 UTC format."
    )
    delay_minutes: Optional[float] = Field(
        None, description="Calculated delay in minutes."
    )
    terminal: Optional[str] = None
    gate: Optional[str] = None
    baggage_belt: Optional[str] = None
    origin: Optional[Location] = None
    destination: Optional[Location] = None
    aircraft: Optional[Aircraft] = None
    raw: Optional[Dict[str, Any]] = Field(
        None, description="Raw FlightRadar24 flight data, if requested."
    )


class ScheduleSection(BaseModel):
    """Holds a paginated list of flights for either arrivals or departures."""

    total_available: int = Field(
        description="Total number of flights available from the API for this section."
    )
    offset: int
    limit: int
    returned: int = Field(description="Number of flights returned in this payload.")
    flights: List[Flight]


class AirportMetadata(BaseModel):
    """Core metadata about the requested airport."""

    icao: Optional[str] = None
    iata: Optional[str] = None
    name: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    timezone: Optional[str] = None
    altitude_ft: Optional[int] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class ResponseMetadata(BaseModel):
    """Metadata about the API response itself."""

    retrieved_at: str = Field(
        description="Timestamp of when the data was fetched, in ISO 8601 UTC format."
    )
    icao: str
    direction: Direction


class AirportScheduleResponse(BaseModel):
    """The successful response payload containing airport and flight data."""

    metadata: ResponseMetadata
    airport: AirportMetadata
    departures: Optional[ScheduleSection] = None
    arrivals: Optional[ScheduleSection] = None


class AirportErrorResponse(BaseModel):
    """The error response payload if fetching airport data fails."""

    error: str
    details: str
    icao: str


@lru_cache(maxsize=1)
def _get_api() -> FlightRadar24API:
    return FlightRadar24API()


async def _get_airport_async(icao: str) -> Any:
    api = _get_api()
    loop = asyncio.get_running_loop()
    fetch = partial(api.get_airport, icao.upper(), details=True)
    return await loop.run_in_executor(None, fetch)


def _get_nested(source: Any, *keys: str) -> Any:
    value = source
    for key in keys:
        if isinstance(value, dict):
            value = value.get(key)
        else:
            return None
    return value


def _ts_to_iso(timestamp: Optional[int]) -> Optional[str]:
    if not timestamp:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()


def _delay_minutes(
    scheduled: Optional[int], estimated: Optional[int]
) -> Optional[float]:
    if not scheduled or not estimated:
        return None
    return round((estimated - scheduled) / 60.0, 2)


def _drop_none(mapping: Dict[str, Any]) -> Dict[str, Any]:
    return {key: value for key, value in mapping.items() if value is not None}


def _build_location(entry: Any, include_coordinates: bool) -> Optional[Dict[str, Any]]:
    if not isinstance(entry, dict):
        return None
    payload: Dict[str, Any] = {
        "name": entry.get("name"),
        "city": _get_nested(entry, "position", "region", "city"),
        "country": _get_nested(entry, "position", "country", "name"),
        "terminal": _get_nested(entry, "info", "terminal"),
        "gate": _get_nested(entry, "info", "gate"),
        "baggage": _get_nested(entry, "info", "baggage"),
        "iata": entry.get("iata"),
        "icao": entry.get("icao"),
    }
    if include_coordinates:
        payload.update(
            {
                "latitude": _get_nested(entry, "position", "latitude"),
                "longitude": _get_nested(entry, "position", "longitude"),
            }
        )
    cleaned = _drop_none(payload)
    return cleaned if cleaned else None


def _serialize_flight(
    item: Any,
    direction: str,
    include_coordinates: bool,
    include_raw: bool,
) -> Optional[Dict[str, Any]]:
    if not isinstance(item, dict):
        return None
    flight = item.get("flight")
    if not isinstance(flight, dict):
        return None

    scheduled_key = "departure" if direction == "departures" else "arrival"
    scheduled_ts = _get_nested(flight, "time", "scheduled", scheduled_key)
    estimated_ts = _get_nested(flight, "time", "estimated", scheduled_key)

    origin = _build_location(
        _get_nested(flight, "airport", "origin"), include_coordinates
    )
    destination = _build_location(
        _get_nested(flight, "airport", "destination"), include_coordinates
    )

    status_text = _get_nested(flight, "status", "generic", "status", "text")
    if isinstance(status_text, str):
        status_text = status_text.capitalize()

    aircraft_details = {
        "model": _get_nested(flight, "aircraft", "model", "text"),
        "registration": _get_nested(flight, "aircraft", "registration"),
        "hex": _get_nested(flight, "aircraft", "hex"),
    }
    aircraft = _drop_none(aircraft_details)

    result: Dict[str, Any] = _drop_none(
        {
            "airline": _get_nested(flight, "airline", "name"),
            "flight_number": _get_nested(flight, "identification", "number", "default"),
            "callsign": _get_nested(flight, "identification", "callsign"),
            "status": status_text,
            "scheduled_time": _ts_to_iso(scheduled_ts),
            "estimated_time": _ts_to_iso(estimated_ts),
            "delay_minutes": _delay_minutes(scheduled_ts, estimated_ts),
            "terminal": (
                _get_nested(flight, "airport", "origin", "info", "terminal")
                if direction == "departures"
                else _get_nested(flight, "airport", "destination", "info", "terminal")
            ),
            "gate": (
                _get_nested(flight, "airport", "origin", "info", "gate")
                if direction == "departures"
                else _get_nested(flight, "airport", "destination", "info", "gate")
            ),
            "baggage_belt": (
                _get_nested(flight, "airport", "destination", "info", "baggage")
                if direction == "arrivals"
                else None
            ),
            "origin": origin,
            "destination": destination,
            "aircraft": aircraft if aircraft else None,
        }
    )

    if include_raw:
        result["raw"] = flight

    return result


def _normalize_limit(limit: int) -> int:
    if limit <= 0:
        raise ValueError("limit must be greater than zero")
    return min(limit, MAX_LIMIT)


def _normalize_offset(offset: int) -> int:
    if offset < 0:
        raise ValueError("offset cannot be negative")
    return offset


def _build_schedule_section(
    schedule: Any,
    direction: str,
    limit: int,
    offset: int,
    include_coordinates: bool,
    include_raw: bool,
) -> Dict[str, Any]:
    if isinstance(schedule, dict):
        data = schedule.get("data", [])
        total = len(data)
    else:
        return {
            "total_available": 0,
            "offset": 0,
            "limit": 0,
            "returned": 0,
            "flights": [],
        }

    limit = _normalize_limit(limit)
    offset = _normalize_offset(offset)

    sliced = data[offset : offset + limit]
    flights = [
        flight
        for flight in (
            _serialize_flight(entry, direction, include_coordinates, include_raw)
            for entry in sliced
        )
        if flight
    ]

    return {
        "total_available": total,
        "offset": offset,
        "limit": limit,
        "returned": len(flights),
        "flights": flights,
    }


def _serialize_airport_metadata(
    airport: Any, include_coordinates: bool
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "icao": getattr(airport, "icao", None),
        "iata": getattr(airport, "iata", None),
        "name": getattr(airport, "name", None),
        "city": getattr(airport, "city", None),
        "country": getattr(airport, "country", None),
        "timezone": getattr(airport, "timezone", None),
        "altitude_ft": getattr(airport, "altitude", None),
    }
    if include_coordinates:
        payload.update(
            {
                "latitude": getattr(airport, "latitude", None),
                "longitude": getattr(airport, "longitude", None),
            }
        )
    return _drop_none(payload)


@mcp.tool(
    name="airport_schedule_lookup",
)
async def airport_schedule_lookup(
    direction: Direction = "both",
    departures_limit: int = 20,
    departures_offset: int = 0,
    arrivals_limit: int = 20,
    arrivals_offset: int = 0,
    include_coordinates: bool = True,
    include_raw: bool = False,
) -> Union[AirportScheduleResponse, AirportErrorResponse]:
    """
    Fetch Mumbai airport schedule data (arrivals/departures) using the FlightRadar24 public API wrapper.
    This tool is specifically configured for Mumbai's Chhatrapati Shivaji Maharaj International Airport (VABB).

    **TOOL SIGNATURE:**
    ```python
    airport_schedule_lookup(
        direction: Literal["both", "arrivals", "departures"] = "both",
        departures_limit: int = 20,  # Max 50
        departures_offset: int = 0,
        arrivals_limit: int = 20,    # Max 50
        arrivals_offset: int = 0,
        include_coordinates: bool = True,
        include_raw: bool = False
    ) -> Union[AirportScheduleResponse, AirportErrorResponse]
    ```

    **PARAMETERS:**
    - direction (str): Scope - "arrivals", "departures", or "both"
    - departures_limit (int): Max departures to return (max 50)
    - departures_offset (int): Skip N departures for pagination
    - arrivals_limit (int): Max arrivals to return (max 50)
    - arrivals_offset (int): Skip N arrivals for pagination
    - include_coordinates (bool): Include lat/lon in location data
    - include_raw (bool): Append raw FlightRadar24 payload per flight

    **RETURNS:**
    On success - AirportScheduleResponse:
    {
        "metadata": {
            "retrieved_at": str,  # ISO 8601 UTC
            "icao": "VABB",
            "direction": str
        },
        "airport": {
            "icao": "VABB",
            "iata": "BOM",
            "name": str,
            "city": "Mumbai",
            "country": "India",
            "timezone": str,
            "altitude_ft": int,
            "latitude": Optional[float],
            "longitude": Optional[float]
        },
        "departures": Optional[{
            "total_available": int,
            "offset": int,
            "limit": int,
            "returned": int,
            "flights": [Flight]
        }],
        "arrivals": Optional[{
            "total_available": int,
            "offset": int,
            "limit": int,
            "returned": int,
            "flights": [Flight]
        }]
    }

    Flight structure:
    {
        "airline": str,
        "flight_number": str,
        "callsign": str,
        "status": str,
        "scheduled_time": str,  # ISO 8601
        "estimated_time": str,  # ISO 8601
        "delay_minutes": float,
        "terminal": str,
        "gate": str,
        "baggage_belt": str,
        "origin": Location,
        "destination": Location,
        "aircraft": {
            "model": str,
            "registration": str,
            "hex": str
        },
        "raw": Optional[Dict]
    }

    On error - AirportErrorResponse:
    {
        "error": str,
        "details": str,
        "icao": "VABB"
    }

    **USAGE EXAMPLES:**

    Example 1 - Mumbai arrivals:
    ```python
    result = await airport_schedule_lookup(
        direction="arrivals",
        arrivals_limit=10
    )
    # Returns next 10 arriving flights at Mumbai
    ```

    Example 2 - Departures only with pagination:
    ```python
    result = await airport_schedule_lookup(
        direction="departures",
        departures_limit=25,
        departures_offset=25
    )
    # Returns departures 26-50
    ```

    Example 3 - Both directions with minimal data:
    ```python
    result = await airport_schedule_lookup(
        direction="both",
        include_coordinates=False,
        include_raw=False
    )
    # Compact response for Mumbai airport
    ```

    Example 4 - Full details with raw data:
    ```python
    result = await airport_schedule_lookup(
        arrivals_limit=5,
        include_raw=True
    )
    # Includes complete FlightRadar24 payloads
    ```

    **ERROR CONDITIONS:**
    - ValueError: Invalid direction value
    - Exception: Network error or API unavailable
    - Returns AirportErrorResponse with error details
    """

    icao = "VABB"  # Mumbai's Chhatrapati Shivaji Maharaj International Airport

    if direction not in {"both", "arrivals", "departures"}:
        raise ValueError("direction must be one of 'both', 'arrivals', or 'departures'")

    try:
        airport = await _get_airport_async(icao)
    except Exception as exc:
        return {
            "error": "Unable to fetch airport data",
            "details": str(exc),
            "icao": icao,
        }

    timestamp = datetime.now(timezone.utc).isoformat()

    result: Dict[str, Any] = {
        "metadata": {
            "retrieved_at": timestamp,
            "icao": icao.upper(),
            "direction": direction,
        },
        "airport": _serialize_airport_metadata(airport, include_coordinates),
    }

    if direction in {"both", "departures"}:
        departures_data = airport.departures if hasattr(airport, "departures") else {}
        result["departures"] = _build_schedule_section(
            departures_data,
            "departures",
            departures_limit,
            departures_offset,
            include_coordinates,
            include_raw,
        )

    if direction in {"both", "arrivals"}:
        arrivals_data = airport.arrivals if hasattr(airport, "arrivals") else {}
        result["arrivals"] = _build_schedule_section(
            arrivals_data,
            "arrivals",
            arrivals_limit,
            arrivals_offset,
            include_coordinates,
            include_raw,
        )

    return result
