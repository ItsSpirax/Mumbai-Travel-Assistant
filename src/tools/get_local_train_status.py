import asyncio
from datetime import datetime, timezone
from functools import partial
from typing import Any, Dict, List, Optional, Union

import requests
from pydantic import BaseModel, Field

from app import mcp

API_URL = "https://railradar.in/api/v1/trains/live-map"


class TrainLocation(BaseModel):
    """Represents the current location of a train."""

    current_station_name: Optional[str] = None
    current_station_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class TrainDetails(BaseModel):
    """Represents details of a single Mumbai local train."""

    train_number: str
    train_name: str
    train_type: Optional[str] = None
    current_station_name: Optional[str] = None
    current_station_code: Optional[str] = None
    speed: Optional[float] = Field(None, description="Current speed in km/h")
    delay_minutes: Optional[int] = Field(None, description="Delay in minutes")
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    raw: Optional[Dict[str, Any]] = Field(None, description="Raw API data if requested")


class TrainStatusResponse(BaseModel):
    """Successful response containing train status data."""

    metadata: Dict[str, Any] = Field(
        description="Metadata about the request and response"
    )
    total_found: int = Field(description="Total number of trains found")
    trains: List[TrainDetails]


class TrainErrorResponse(BaseModel):
    """Error response if fetching train data fails."""

    error: str
    details: str


def _fetch_train_data() -> Dict[str, Any]:
    """Synchronously fetch train data from API."""
    response = requests.get(API_URL, timeout=10)
    response.raise_for_status()
    return response.json()


async def _fetch_train_data_async() -> Dict[str, Any]:
    """Asynchronously fetch train data from API."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _fetch_train_data)


def _serialize_train(
    train: Dict[str, Any], include_raw: bool
) -> Optional[Dict[str, Any]]:
    """Serialize a single train entry."""
    if not isinstance(train, dict):
        return None

    result = {
        "train_number": train.get("train_number"),
        "train_name": train.get("train_name"),
        "train_type": train.get("type"),
        "current_station_name": train.get("current_station_name"),
        "current_station_code": train.get("current_station_code"),
        "speed": train.get("speed"),
        "delay_minutes": train.get("delay"),
        "latitude": train.get("lat"),
        "longitude": train.get("lon"),
    }

    if include_raw:
        result["raw"] = train

    return {k: v for k, v in result.items() if v is not None}


@mcp.tool(name="mumbai_local_train_status")
async def mumbai_local_train_status(
    train_number: Optional[str] = None,
    train_name_query: Optional[str] = None,
    current_station_query: Optional[str] = None,
    include_raw: bool = False,
) -> Union[TrainStatusResponse, TrainErrorResponse]:
    """
    Fetch live status of Mumbai local trains from RailRadar API.

    **TOOL SIGNATURE:**
    ```python
    mumbai_local_train_status(
        train_number: Optional[str] = None,
        train_name_query: Optional[str] = None,
        current_station_query: Optional[str] = None,
        include_raw: bool = False
    ) -> Union[TrainStatusResponse, TrainErrorResponse]
    ```

    **PARAMETERS:**
    - train_number (str, optional): Exact train number to search for (e.g., "01155")
    - train_name_query (str, optional): Fuzzy search string for train names (case-insensitive)
    - current_station_query (str, optional): Fuzzy search string for current station names (case-insensitive)
    - include_raw (bool): Include raw API response data per train

    **RETURNS:**
    On success - TrainStatusResponse:
    {
        "metadata": {
            "retrieved_at": str,  # ISO 8601 UTC
            "filters_applied": {
                "train_number": Optional[str],
                "train_name_query": Optional[str],
                "current_station_query": Optional[str]
            }
        },
        "total_found": int,
        "trains": [TrainDetails]
    }

    TrainDetails structure:
    {
        "train_number": str,
        "train_name": str,
        "train_type": str,
        "current_station_name": str,
        "current_station_code": str,
        "speed": float,  # km/h
        "delay_minutes": int,
        "latitude": float,
        "longitude": float,
        "raw": Optional[Dict]  # If include_raw=True
    }

    On error - TrainErrorResponse:
    {
        "error": str,
        "details": str
    }

    **USAGE EXAMPLES:**

    Example 1 - All live Mumbai local trains:
    ```python
    result = await mumbai_local_train_status()
    # Returns all currently running Mumbai EMU trains
    ```

    Example 2 - Specific train by number:
    ```python
    result = await mumbai_local_train_status(train_number="01155")
    # Returns status of train 01155 if it's live
    ```

    Example 3 - Search by name:
    ```python
    result = await mumbai_local_train_status(train_name_query="Diva")
    # Returns all trains with "Diva" in their name
    ```

    Example 4 - Search by current station:
    ```python
    result = await mumbai_local_train_status(current_station_query="Andheri")
    # Returns all trains currently at or near Andheri station
    ```

    Example 5 - Combined filters:
    ```python
    result = await mumbai_local_train_status(
        train_name_query="Local",
        current_station_query="Bandra",
        include_raw=True
    )
    # Returns trains with "Local" in name at Bandra with raw data
    ```

    **MUMBAI RAIL NETWORK CONTEXT:**
    The Mumbai Suburban Railway (local train) network consists of three main lines and several branches. This context provides key stations and interchanges based on the rail map to help understand routes.

    ```json
    {
      "western_line": {
        "terminus": "Churchgate (South)",
        "key_stations": [
          "Churchgate", "Mumbai Central", "Dadar", "Bandra", "Andheri",
          "Borivali", "Virar", "Dahanu Rd. (North)"
        ],
        "type": "Runs North-South"
      },
      "central_line": {
        "terminus": "Mumbai C.S.T. (South)",
        "key_stations_main": [
          "Mumbai C.S.T.", "Byculla", "Dadar", "Kurla", "Ghatkopar",
          "Vikhroli", "Thane", "Dombivli", "Kalyan"
        ],
        "branches_from_kalyan": {
          "northeast_branch": ["Kalyan", "Titwala", "Asangaon", "Kasara"],
          "southeast_branch": ["Kalyan", "Ambernath", "Badlapur", "Karjat", "Khopoli"]
        }
      },
      "harbour_line": {
        "terminus": "Mumbai C.S.T. (South)",
        "key_stations": [
          "Mumbai C.S.T.", "Wadala Rd.", "Kurla", "Mankhurd", "Vashi",
          "Nerul", "Belapur", "Panvel (South-East)"
        ],
        "branches": [
          {
            "type": "Trans-Harbour Line",
            "description": "Connects Thane (Central) to Vashi/Nerul (Harbour)",
            "route": ["Thane", "Airoli", "Rabale", "Ghansoli", "Koparkhairane", "Turbhe", "Vashi"]
          }
        ]
      },
      "key_interchanges": {
        "Dadar": "Western Line & Central Line",
        "Kurla": "Central Line & Harbour Line",
        "Thane": "Central Line & Trans-Harbour Line",
        "Vashi": "Harbour Line & Trans-Harbour Line",
        "Wadala Rd.": "Harbour Line (Main) & Harbour Line (Branch to Kurla/Mankhurd)"
      }
    }
    ```

    **ERROR CONDITIONS:**
    - Network errors or API timeout
    - Invalid API response format
    - Returns TrainErrorResponse with error details
    """

    try:
        api_data = await _fetch_train_data_async()

        if not api_data.get("success") or "data" not in api_data:
            return {
                "error": "API response unsuccessful",
                "details": "The API did not return success=true or data is missing",
            }

        all_trains = api_data["data"]

        mumbai_trains = [
            train for train in all_trains if train.get("type") == "EMU - Mumbai"
        ]

        if train_number:
            mumbai_trains = [
                train
                for train in mumbai_trains
                if train.get("train_number") == train_number
            ]

        if train_name_query:
            query = train_name_query.lower()
            mumbai_trains = [
                train
                for train in mumbai_trains
                if train.get("train_name") and query in train.get("train_name").lower()
            ]

        if current_station_query:
            query = current_station_query.lower()
            mumbai_trains = [
                train
                for train in mumbai_trains
                if train.get("current_station_name")
                and query in train.get("current_station_name").lower()
            ]

        serialized_trains = [
            train
            for train in (_serialize_train(t, include_raw) for t in mumbai_trains)
            if train
        ]

        timestamp = datetime.now(timezone.utc).isoformat()

        return {
            "metadata": {
                "retrieved_at": timestamp,
                "filters_applied": {
                    "train_number": train_number,
                    "train_name_query": train_name_query,
                    "current_station_query": current_station_query,
                },
            },
            "total_found": len(serialized_trains),
            "trains": serialized_trains,
        }

    except requests.exceptions.RequestException as exc:
        return {
            "error": "Network error",
            "details": f"Failed to fetch data from RailRadar API: {str(exc)}",
        }
    except ValueError as exc:
        return {
            "error": "JSON decode error",
            "details": f"Failed to parse API response: {str(exc)}",
        }
    except Exception as exc:
        return {
            "error": "Unexpected error",
            "details": str(exc),
        }
