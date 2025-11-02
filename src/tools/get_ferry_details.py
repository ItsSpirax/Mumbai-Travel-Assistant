from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app import mcp

FERRY_TRIPS: List[Dict[str, Any]] = [
    {
        "from_location": "Gorai Jetty",
        "to_location": "Borivali",
        "origin_first_departure": "05.30 AM",
        "origin_last_departure": "11.45 AM",
        "destination_first_departure": "05.45 AM",
        "destination_last_departure": "12.00 AM",
        "frequency": "05 Mins",
        "journey_time": "05 Mins",
        "fare": "10/-",
        "availability": "365 Days",
        "bikes_allowed": True,
        "bike_details": None,
    },
    {
        "from_location": "Borivali Jetty",
        "to_location": "Essel World",
        "origin_first_departure": "09.40 AM",
        "origin_last_departure": "05.35 PM",
        "destination_first_departure": "10.00 AM",
        "destination_last_departure": "07.35 PM",
        "frequency": "30 Mins",
        "journey_time": "20 Mins",
        "fare": "Return 50/-",
        "availability": "365 Days",
        "bikes_allowed": False,
        "bike_details": None,
    },
    {
        "from_location": "Marve",
        "to_location": "Essel World",
        "origin_first_departure": "09.35 AM",
        "origin_last_departure": "05.00 PM",
        "destination_first_departure": "10.00 AM",
        "destination_last_departure": "07.35 PM",
        "frequency": "40 Mins",
        "journey_time": "25 Mins",
        "fare": "Return 50/-",
        "availability": "365 Days",
        "bikes_allowed": False,
        "bike_details": None,
    },
    {
        "from_location": "Manori",
        "to_location": "Marve",
        "origin_first_departure": "05.15 AM",
        "origin_last_departure": "12.00 AM",
        "destination_first_departure": "05.30 AM",
        "destination_last_departure": "12.20 AM",
        "frequency": "15 Mins",
        "journey_time": "5 Mins",
        "fare": "10/-",
        "availability": "365 Days",
        "bikes_allowed": True,
        "bike_details": None,
    },
    {
        "from_location": "Versova",
        "to_location": "Madh",
        "origin_first_departure": "05.00 AM",
        "origin_last_departure": "01.15 AM",
        "destination_first_departure": "05.15 AM",
        "destination_last_departure": "01.30 AM",
        "frequency": "15 Mins",
        "journey_time": "5 Mins",
        "fare": "3/-",
        "availability": "365 Days",
        "bikes_allowed": True,
        "bike_details": None,
    },
    {
        "from_location": "Panju Island",
        "to_location": "Naigaon Jetty",
        "origin_first_departure": "06.00 AM",
        "origin_last_departure": "09.55 PM",
        "destination_first_departure": "06.05 AM",
        "destination_last_departure": "10.00 PM",
        "frequency": "30 Mins",
        "journey_time": "5 Mins",
        "fare": "10/-",
        "availability": "365 Days",
        "bikes_allowed": False,
        "bike_details": None,
    },
    {
        "from_location": "Arnala",
        "to_location": "Arnala Fort",
        "origin_first_departure": "06.00 AM",
        "origin_last_departure": "06.15 PM",
        "destination_first_departure": "06.15 AM",
        "destination_last_departure": "06.30 PM",
        "frequency": "15 Mins",
        "journey_time": "5 Mins",
        "fare": "5/-",
        "availability": "365 Days",
        "bikes_allowed": False,
        "bike_details": None,
    },
    {
        "from_location": "Navapur",
        "to_location": "Dandi",
        "origin_first_departure": "06.00 AM",
        "origin_last_departure": "06.45 PM",
        "destination_first_departure": "06.15 AM",
        "destination_last_departure": "07.00 PM",
        "frequency": "15 Mins",
        "journey_time": "5 Mins",
        "fare": "1/-",
        "availability": "365 Days",
        "bikes_allowed": False,
        "bike_details": None,
    },
    {
        "from_location": "Murbe",
        "to_location": "Satpati",
        "origin_first_departure": "07.30 AM",
        "origin_last_departure": "07.15 PM",
        "destination_first_departure": "07.45 AM",
        "destination_last_departure": "07.30 PM",
        "frequency": "15 Mins",
        "journey_time": "5 Mins",
        "fare": "1/-",
        "availability": "365 Days",
        "bikes_allowed": False,
        "bike_details": None,
    },
    {
        "from_location": "Murbe",
        "to_location": "Kharekuran",
        "origin_first_departure": "07.30 AM",
        "origin_last_departure": "06.15 PM",
        "destination_first_departure": "07.45 AM",
        "destination_last_departure": "06.30 PM",
        "frequency": "15 Mins",
        "journey_time": "5 Mins",
        "fare": "1/-",
        "availability": "365 Days",
        "bikes_allowed": False,
        "bike_details": None,
    },
    {
        "from_location": "Karanja",
        "to_location": "Rewas",
        "origin_first_departure": "07.30 AM",
        "origin_last_departure": "06.30 PM",
        "destination_first_departure": "07.15 AM",
        "destination_last_departure": "06.00 PM",
        "frequency": "1 Hour",
        "journey_time": "15 Mins",
        "fare": "30/-",
        "availability": "365 Days",
        "bikes_allowed": True,
        "bike_details": None,
    },
    {
        "from_location": "Belapur",
        "to_location": "Elephanta",
        "origin_first_departure": "09.30 AM",
        "origin_last_departure": "09.30 AM",
        "destination_first_departure": "01.00 PM (Tue to Fri)",
        "destination_last_departure": "05.30 PM (Sat, Sun, Holiday)",
        "frequency": "Schedule changes frequently",
        "journey_time": "45 Mins",
        "fare": "825/-",
        "availability": None,
        "bikes_allowed": False,
        "bike_details": None,
    },
    {
        "from_location": "Belapur",
        "to_location": "JNPT",
        "origin_first_departure": "09.30 AM",
        "origin_last_departure": "09.30 AM",
        "destination_first_departure": "01.00 PM (Tue to Fri)",
        "destination_last_departure": "05.30 PM (Sat, Sun, Holiday)",
        "frequency": "Schedule changes frequently",
        "journey_time": "30 Mins",
        "fare": "825/-",
        "availability": None,
        "bikes_allowed": False,
        "bike_details": None,
    },
    {
        "from_location": "Belapur",
        "to_location": "Elephanta",
        "origin_first_departure": "09.30 AM",
        "origin_last_departure": "09.30 AM",
        "destination_first_departure": "01.00 PM (Tue to Fri)",
        "destination_last_departure": "05.30 PM (Sat, Sun, Holiday)",
        "frequency": "Depends on passenger availability",
        "journey_time": "30 Mins",
        "fare": "400/-",
        "availability": "Closed on Monday",
        "bikes_allowed": False,
        "bike_details": None,
    },
    {
        "from_location": "Gateway",
        "to_location": "Mandwa (Alibaug)",
        "origin_first_departure": "06.15 AM",
        "origin_last_departure": "08.15 PM",
        "destination_first_departure": "07.10 AM",
        "destination_last_departure": "07.30 PM",
        "frequency": "1 Hour",
        "journey_time": "1 Hour 30 Mins",
        "fare": "135/- to 185/-",
        "availability": "Closed in Monsoon",
        "bikes_allowed": False,
        "bike_details": None,
    },
    {
        "from_location": "Gateway",
        "to_location": "Elephanta",
        "origin_first_departure": "09.00 AM",
        "origin_last_departure": "03.20 PM",
        "destination_first_departure": "12.00 PM",
        "destination_last_departure": "06.30 PM",
        "frequency": "15/30 Mins",
        "journey_time": "1 Hour",
        "fare": "Return 200/-",
        "availability": "365 Days",
        "bikes_allowed": False,
        "bike_details": None,
    },
    {
        "from_location": "Bhauch Dhakka (New Ferry Wharf)",
        "to_location": "Rewas",
        "origin_first_departure": "06.00 AM",
        "origin_last_departure": "05.00 PM",
        "destination_first_departure": "07.45 AM",
        "destination_last_departure": "06.30 PM",
        "frequency": "1 Hour",
        "journey_time": "1 Hour 30 Mins",
        "fare": "73/-",
        "availability": "Closed in Monsoon",
        "bikes_allowed": True,
        "bike_details": None,
    },
    {
        "from_location": "Bhauch Dhakka (New Ferry Wharf)",
        "to_location": "Mora",
        "origin_first_departure": "08.25 AM",
        "origin_last_departure": "08.45 PM",
        "destination_first_departure": "07.30 AM",
        "destination_last_departure": "08.00 PM",
        "frequency": "1 Hour",
        "journey_time": "1 Hour",
        "fare": "55/- fair (70/- foul)",
        "availability": "365 Days",
        "bikes_allowed": True,
        "bike_details": None,
    },
    {
        "from_location": "Bhauch Dhakka (New Ferry Wharf)",
        "to_location": "Mora",
        "origin_first_departure": "06.00 AM",
        "origin_last_departure": "08.15 PM",
        "destination_first_departure": "07.00 AM",
        "destination_last_departure": "09.15 PM",
        "frequency": "30 Mins",
        "journey_time": "1 Hour",
        "fare": "48/- fair (66/- foul)",
        "availability": "365 Days",
        "bikes_allowed": True,
        "bike_details": None,
    },
    {
        "from_location": "Bhauch Dhakka (New Ferry Wharf)",
        "to_location": "Elephanta",
        "origin_first_departure": "Depends on passenger availability",
        "origin_last_departure": None,
        "destination_first_departure": "Depends on passenger availability",
        "destination_last_departure": None,
        "frequency": "Depends on passenger availability",
        "journey_time": "1 Hour 30 Mins",
        "fare": "Return 160/-",
        "availability": "365 Days",
        "bikes_allowed": False,
        "bike_details": None,
    },
    {
        "from_location": "Mora",
        "to_location": "Elephanta",
        "origin_first_departure": "06.30 AM",
        "origin_last_departure": "04.30 PM",
        "destination_first_departure": "07.15 AM",
        "destination_last_departure": "05.15 PM",
        "frequency": "1 Hour",
        "journey_time": "45 Mins",
        "fare": "Return 45/-",
        "availability": "365 Days",
        "bikes_allowed": False,
        "bike_details": None,
    },
    {
        "from_location": "Mora",
        "to_location": "Sassoon Dock",
        "origin_first_departure": "04.30 AM",
        "origin_last_departure": "06.00 PM",
        "destination_first_departure": "05.30 AM",
        "destination_last_departure": "07.00 PM",
        "frequency": "1 Hour",
        "journey_time": "1 Hour",
        "fare": "50/-",
        "availability": "365 Days",
        "bikes_allowed": False,
        "bike_details": None,
    },
    {
        "from_location": "Rajpuri",
        "to_location": "Dighi",
        "origin_first_departure": "07.00 AM",
        "origin_last_departure": "05.30 PM",
        "destination_first_departure": "07.30 AM",
        "destination_last_departure": "06.00 PM",
        "frequency": "1 Hour",
        "journey_time": "25 Mins",
        "fare": "22/-",
        "availability": "Closed in Monsoon",
        "bikes_allowed": False,
        "bike_details": None,
    },
    {
        "from_location": "Dighi",
        "to_location": "Janjira Fort",
        "origin_first_departure": "07.00 AM",
        "origin_last_departure": "04.30 PM",
        "destination_first_departure": "07.30 AM",
        "destination_last_departure": "05.00 PM",
        "frequency": "Depends on passenger availability",
        "journey_time": "30 Mins",
        "fare": "100/-",
        "availability": "Closed in Monsoon",
        "bikes_allowed": False,
        "bike_details": None,
    },
    {
        "from_location": "Rajpuri",
        "to_location": "Janjira Fort",
        "origin_first_departure": "08.00 AM",
        "origin_last_departure": "04.45 PM",
        "destination_first_departure": "08.15 AM",
        "destination_last_departure": "05.00 PM",
        "frequency": "Depends on passenger availability",
        "journey_time": "15 Mins",
        "fare": "61/-",
        "availability": "Closed in Monsoon",
        "bikes_allowed": False,
        "bike_details": None,
    },
    {
        "from_location": "Dighi",
        "to_location": "Agardanda",
        "origin_first_departure": "07.30 AM",
        "origin_last_departure": "06.00 PM",
        "destination_first_departure": "07.45 AM",
        "destination_last_departure": "06.30 PM",
        "frequency": "1 Hour 30 Mins",
        "journey_time": "20 Mins",
        "fare": "14/-",
        "availability": "365 Days",
        "bikes_allowed": False,
        "bike_details": None,
    },
    {
        "from_location": "Dighi",
        "to_location": "Agardanda",
        "origin_first_departure": "07.15 AM",
        "origin_last_departure": "06.15 PM",
        "destination_first_departure": "08.15 AM",
        "destination_last_departure": "07.00 PM",
        "frequency": "1 Hour 30 Mins",
        "journey_time": "20 Mins",
        "fare": "20/-",
        "availability": "365 Days",
        "bikes_allowed": True,
        "bike_details": "50/-",
    },
    {
        "from_location": "Dabhol",
        "to_location": "Dhopawe",
        "origin_first_departure": "06.30 AM",
        "origin_last_departure": "10.00 PM",
        "destination_first_departure": "06.45 AM",
        "destination_last_departure": "10.10 PM",
        "frequency": "1 Hour",
        "journey_time": "10 Mins",
        "fare": "10.50/-",
        "availability": "365 Days",
        "bikes_allowed": True,
        "bike_details": "40/-",
    },
    {
        "from_location": "Veshvi",
        "to_location": "Bagmandla",
        "origin_first_departure": "06.00 AM",
        "origin_last_departure": "10.00 PM",
        "destination_first_departure": "07.30 AM",
        "destination_last_departure": "10.10 PM",
        "frequency": "1 Hour",
        "journey_time": "10 Mins",
        "fare": "10.50/-",
        "availability": "365 Days",
        "bikes_allowed": True,
        "bike_details": "40/-",
    },
    {
        "from_location": "Jaigad",
        "to_location": "Tavsal",
        "origin_first_departure": "07.00 AM",
        "origin_last_departure": "10.15 PM",
        "destination_first_departure": "06.45 AM",
        "destination_last_departure": "10.00 PM",
        "frequency": "Depends on passenger availability",
        "journey_time": "15 Mins",
        "fare": "21/-",
        "availability": "365 Days",
        "bikes_allowed": True,
        "bike_details": "50/-",
    },
    {
        "from_location": "Malvan",
        "to_location": "Sindhudurg Fort",
        "origin_first_departure": "06.00 AM",
        "origin_last_departure": "05.50 PM",
        "destination_first_departure": "07.30 AM",
        "destination_last_departure": "06.30 PM",
        "frequency": "Depends on passenger availability",
        "journey_time": "10 Mins",
        "fare": "Return 70/-",
        "availability": "365 Days",
        "bikes_allowed": False,
        "bike_details": None,
    },
    {
        "from_location": "Agardanda",
        "to_location": "Rohini",
        "origin_first_departure": "07.00 AM",
        "origin_last_departure": None,
        "destination_first_departure": "06.00 PM",
        "destination_last_departure": None,
        "frequency": "Depends on passenger availability",
        "journey_time": "25 Mins",
        "fare": "20/-",
        "availability": "365 Days",
        "bikes_allowed": True,
        "bike_details": "50/-",
    },
    {
        "from_location": "Bhayandar",
        "to_location": "Vasai",
        "origin_first_departure": "07.30 AM",
        "origin_last_departure": "07.30 PM",
        "destination_first_departure": "06.45 AM",
        "destination_last_departure": "06.45 PM",
        "frequency": "1 Hour 30 Mins",
        "journey_time": "10-15 Mins",
        "fare": "25/-",
        "availability": "365 Days",
        "bikes_allowed": True,
        "bike_details": "50/-",
    },
]

SORTABLE_FIELDS = {"from_location", "to_location", "frequency", "journey_time"}


def _normalize_value(value: Optional[str]) -> str:
    return value.strip().lower() if isinstance(value, str) else ""


def _filter_trip(
    trip: Dict[str, Any],
    from_location: Optional[str],
    to_location: Optional[str],
    allows_bikes: Optional[bool],
    availability: Optional[str],
) -> bool:
    if from_location:
        if _normalize_value(from_location) not in _normalize_value(
            trip["from_location"]
        ):
            return False
    if to_location:
        if _normalize_value(to_location) not in _normalize_value(trip["to_location"]):
            return False
    if allows_bikes is not None:
        if trip["bikes_allowed"] is None:
            return False
        if trip["bikes_allowed"] != allows_bikes:
            return False
    if availability:
        if _normalize_value(availability) not in _normalize_value(
            trip.get("availability")
        ):
            return False
    return True


def _prepare_trip(trip: Dict[str, Any]) -> Dict[str, Any]:
    payload = dict(trip)
    payload["bike_details"] = trip["bike_details"] or None
    payload["availability"] = trip["availability"] or None
    return payload


@mcp.tool(name="ferry_schedule_lookup")
async def ferry_schedule_lookup(
    from_location: Optional[str] = None,
    to_location: Optional[str] = None,
    allows_bikes: Optional[bool] = None,
    availability: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    sort_by: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Return reference ferry timings for the Mumbai region sourced from the static transport schedule dataset.

    **TOOL SIGNATURE:**
    ```python
    ferry_schedule_lookup(
        from_location: Optional[str] = None,
        to_location: Optional[str] = None,
        allows_bikes: Optional[bool] = None,
        availability: Optional[str] = None,
        limit: int = 20,  # Max 50
        offset: int = 0,  # Must be >= 0
        sort_by: Optional[Literal["from_location", "to_location", "frequency", "journey_time"]] = None
    ) -> Dict[str, Any]
    ```

    **PARAMETERS:**
    - from_location (str, optional): Filter by origin name (case-insensitive substring match)
    - to_location (str, optional): Filter by destination name (case-insensitive substring match)
    - allows_bikes (bool, optional): Filter ferries that allow/disallow bikes
    - availability (str, optional): Filter by availability notes (e.g., "Monsoon", "365 Days")
    - limit (int): Max entries to return (default 20, max 50, must be > 0)
    - offset (int): Skip N filtered entries (must be >= 0)
    - sort_by (str, optional): Sort field - one of: from_location, to_location, frequency, journey_time

    **RETURNS:**
    Dict[str, Any]:
    {
        "metadata": {
            "retrieved_at": str,  # ISO 8601 UTC timestamp
            "total": int,         # Total matching records
            "returned": int,      # Records in this response
            "limit": int,
            "offset": int
        },
        "filters": {
            # Applied filters (only non-null values)
            "from_location": Optional[str],
            "to_location": Optional[str],
            "allows_bikes": Optional[bool],
            "availability": Optional[str],
            "sort_by": Optional[str]
        },
        "results": [
            {
                "from_location": str,
                "to_location": str,
                "origin_first_departure": str,
                "origin_last_departure": str,
                "destination_first_departure": str,
                "destination_last_departure": str,
                "frequency": str,
                "journey_time": str,
                "fare": str,
                "availability": Optional[str],
                "bikes_allowed": bool,
                "bike_details": Optional[str]
            }
        ]
    }

    **USAGE EXAMPLES:**

    Example 1 - All ferries from Gateway:
    ```python
    result = await ferry_schedule_lookup(from_location="Gateway")
    # Returns all ferries departing from Gateway of India
    ```

    Example 2 - Bike-friendly ferries:
    ```python
    result = await ferry_schedule_lookup(allows_bikes=True, limit=10)
    # Returns up to 10 ferries that allow bikes
    ```

    Example 3 - Monsoon-affected routes:
    ```python
    result = await ferry_schedule_lookup(availability="Monsoon", limit=15)
    # Returns ferries with "Monsoon" in availability notes
    ```

    Example 4 - Paginated and sorted results:
    ```python
    result = await ferry_schedule_lookup(
        sort_by="journey_time",
        limit=10,
        offset=10
    )
    # Returns records 11-20, sorted by journey time
    ```

    Example 5 - Specific route search:
    ```python
    result = await ferry_schedule_lookup(
        from_location="Gorai",
        to_location="Borivali"
    )
    # Returns ferries from Gorai to Borivali area
    ```

    **COMMON ROUTES:**
    - Gateway ↔ Elephanta Island
    - Gateway ↔ Mandwa (Alibaug)
    - Gorai ↔ Borivali
    - Versova ↔ Madh
    - Mora ↔ Elephanta

    **ERROR CONDITIONS:**
    - ValueError: limit <= 0 or offset < 0
    - ValueError: sort_by not in allowed fields
    """

    if limit <= 0:
        raise ValueError("limit must be greater than zero")
    limit = min(limit, 50)
    if offset < 0:
        raise ValueError("offset cannot be negative")

    filtered = [
        _prepare_trip(trip)
        for trip in FERRY_TRIPS
        if _filter_trip(trip, from_location, to_location, allows_bikes, availability)
    ]

    total = len(filtered)

    if sort_by:
        if sort_by not in SORTABLE_FIELDS:
            raise ValueError(f"sort_by must be one of {sorted(SORTABLE_FIELDS)}")
        filtered.sort(key=lambda item: _normalize_value(item.get(sort_by)))

    paginated = filtered[offset : offset + limit]

    metadata = {
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "total": total,
        "returned": len(paginated),
        "limit": limit,
        "offset": offset,
    }

    filters = {
        "from_location": from_location,
        "to_location": to_location,
        "allows_bikes": allows_bikes,
        "availability": availability,
        "sort_by": sort_by,
    }

    return {
        "metadata": metadata,
        "filters": {key: value for key, value in filters.items() if value is not None},
        "results": paginated,
    }
