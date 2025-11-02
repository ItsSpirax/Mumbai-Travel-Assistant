from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import httpx

from app import app_state, mcp


RAILRADAR_URL = "https://railjournal.in/RailRadar/fetch_trains_at_stn.php"

STATION_DIRECTORY: Dict[str, Dict[str, Any]] = {
    "DR": {
        "name": "Dadar",
        "aliases": ["dadar", "dr"],
    },
    "MMCT": {
        "name": "Mumbai Central",
        "aliases": ["mumbai central", "mmct"],
    },
    "CSMT": {
        "name": "Chhatrapati Shivaji Maharaj Terminus",
        "aliases": ["csmt", "cst", "vt", "chhatrapati shivaji maharaj terminus"],
    },
    "BDTS": {
        "name": "Bandra Terminus",
        "aliases": ["bandra terminus", "bdts"],
    },
    "LTT": {
        "name": "Lokmanya Tilak Terminus",
        "aliases": ["ltt", "lokmanya tilak", "kalyan shilphata"],
    },
    "TNA": {
        "name": "Thane",
        "aliases": ["thane", "tna"],
    },
}


def _build_alias_index() -> Dict[str, str]:
    alias_index: Dict[str, str] = {}
    for code, payload in STATION_DIRECTORY.items():
        alias_index[code.lower()] = code
        alias_index[payload["name"].lower()] = code
        for alias in payload.get("aliases", []):
            alias_index[alias.lower()] = code
    return alias_index


ALIAS_TO_CODE = _build_alias_index()


def _select_client() -> httpx.AsyncClient:
    if app_state.http_client is None:
        app_state.http_client = httpx.AsyncClient(timeout=30.0)
    return app_state.http_client


def _safe_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        return int(str(value).strip())
    except (ValueError, TypeError):
        return None


def _drop_empty(mapping: Dict[str, Any]) -> Dict[str, Any]:
    return {
        key: value for key, value in mapping.items() if value not in (None, "", [], {})
    }


def _resolve_station(station: str) -> Tuple[str, Dict[str, Any]]:
    if not station:
        raise ValueError("station must be provided")
    code = ALIAS_TO_CODE.get(station.strip().lower())
    if code is None:
        supported = ", ".join(
            f"{info['name']} ({key})" for key, info in STATION_DIRECTORY.items()
        )
        raise ValueError(
            f"Unsupported station '{station}'. Supported options: {supported}"
        )
    return code, STATION_DIRECTORY[code]


def _categorise_status(status: Optional[str]) -> str:
    if not status:
        return "unknown"
    status_lower = status.lower()
    if "arriv" in status_lower:
        return "arrived"
    if "depart" in status_lower or "left" in status_lower:
        return "departed"
    if "on time" in status_lower or "right time" in status_lower:
        return "on_time"
    if "late" in status_lower or "delay" in status_lower:
        return "delayed"
    if "cancel" in status_lower:
        return "cancelled"
    return "other"


def _parse_board_entries(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    for item in payload.get("live", []) or []:
        if not isinstance(item, dict):
            continue
        entry = _drop_empty(
            {
                "train_name": item.get("Train"),
                "expected_time": item.get("Expected"),
                "status": item.get("Current"),
                "platform": item.get("PF") or None,
            }
        )
        if entry:
            entry["status_bucket"] = _categorise_status(entry.get("status"))
            entries.append(entry)
    return entries


def _summarise_board(entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    counts: Dict[str, int] = {}
    for item in entries:
        bucket = item.get("status_bucket", "unknown")
        counts[bucket] = counts.get(bucket, 0) + 1
    platforms = sorted(
        {entry["platform"] for entry in entries if entry.get("platform")}
    )
    return {
        "total_trains": len(entries),
        "status_breakdown": counts,
        "platforms_announced": platforms,
    }


SUPPORTED_STATIONS_TEXT = ", ".join(
    info["name"] + f" ({code})" for code, info in STATION_DIRECTORY.items()
)


@mcp.tool(name="station_board_lookup")
async def station_board_lookup(
    station: str = "DR",
    next_minutes: Optional[int] = 120,
    include_raw: bool = False,
) -> Dict[str, Any]:
    """
    Retrieve live train board information for supported Mumbai suburban and long-distance stations.

    **TOOL SIGNATURE:**
    ```python
    station_board_lookup(
        station: str = "DR",
        next_minutes: Optional[int] = 120,  # Must be > 0 if provided
        include_raw: bool = False
    ) -> Dict[str, Any]
    ```

    **PARAMETERS:**
    - station (str): Station code or name (case-insensitive)
      Supported stations:
      * "DR" / "Dadar"
      * "MMCT" / "Mumbai Central"
      * "CSMT" / "CST" / "VT" / "Chhatrapati Shivaji Maharaj Terminus"
      * "BDTS" / "Bandra Terminus"
      * "LTT" / "Lokmanya Tilak Terminus"
      * "TNA" / "Thane"
    - next_minutes (int, optional): Future time window in minutes (must be > 0)
    - include_raw (bool): Include full RailRadar API response

    **RETURNS:**
    Dict[str, Any]:
    {
        "metadata": {
            "station_code": str,
            "station_name": str,
            "aliases": List[str],
            "requested_window_minutes": Optional[int],
            "reported_window_minutes": Optional[int],
            "http_code": Optional[int],
            "source": str  # API URL
        },
        "summary": {
            "total_trains": int,
            "status_breakdown": {
                "on_time": int,
                "delayed": int,
                "arrived": int,
                "departed": int,
                "cancelled": int,
                "other": int,
                "unknown": int
            },
            "platforms_announced": List[str]
        },
        "board": [
            {
                "train_name": str,
                "expected_time": str,
                "status": str,
                "platform": Optional[str],
                "status_bucket": str  # Categorized status
            }
        ],
        "raw": Optional[Dict]  # If include_raw=True
    }

    **USAGE EXAMPLES:**

    Example 1 - Current board at Dadar:
    ```python
    result = await station_board_lookup(station="DR")
    # Returns live board with 2-hour window
    ```

    Example 2 - Using station name:
    ```python
    result = await station_board_lookup(station="Mumbai Central")
    # Case-insensitive, accepts full names
    ```

    Example 3 - Custom time window:
    ```python
    result = await station_board_lookup(
        station="CSMT",
        next_minutes=60
    )
    # Only trains within next 60 minutes
    ```

    Example 4 - With raw API data:
    ```python
    result = await station_board_lookup(
        station="Thane",
        include_raw=True
    )
    # Includes complete RailRadar response
    ```

    Example 5 - Check specific platforms:
    ```python
    result = await station_board_lookup(station="LTT")
    platforms = result["summary"]["platforms_announced"]
    # Returns list of active platforms
    ```

    **STATUS CATEGORIES:**
    - on_time: Train running on schedule
    - delayed: Train running late
    - arrived: Train has arrived
    - departed: Train has left
    - cancelled: Service cancelled
    - other: Other status messages
    - unknown: Status unclear

    **ERROR CONDITIONS:**
    - ValueError: Unsupported station name/code
    - ValueError: next_minutes <= 0
    - Network error: Returns error dict with details
    - Invalid JSON: Returns error dict with parsing details
    """

    code, station_meta = _resolve_station(station)

    if next_minutes is not None and next_minutes <= 0:
        raise ValueError("next_minutes must be greater than zero when provided")

    params = {"stn": code}
    if next_minutes is not None:
        params["nextMinutes"] = str(next_minutes)

    client = _select_client()

    try:
        response = await client.get(
            RAILRADAR_URL,
            params=params,
            headers={"Accept": "application/json"},
        )
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPError as exc:
        return {
            "error": "Unable to reach RailRadar",
            "details": str(exc),
            "station": code,
        }
    except ValueError as exc:
        return {
            "error": "Unexpected RailRadar response",
            "details": str(exc),
            "station": code,
        }

    entries = _parse_board_entries(payload)
    metadata = {
        "station_code": code,
        "station_name": station_meta["name"],
        "aliases": station_meta.get("aliases", []),
        "requested_window_minutes": next_minutes,
        "reported_window_minutes": _safe_int(payload.get("nextMinutes")),
        "http_code": _safe_int(payload.get("http_code")),
        "source": RAILRADAR_URL,
    }

    result: Dict[str, Any] = {
        "metadata": _drop_empty(metadata),
        "summary": _summarise_board(entries),
        "board": entries,
    }

    if include_raw:
        result["raw"] = payload

    return result
