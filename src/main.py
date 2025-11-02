from importlib import import_module

from starlette.requests import Request
from starlette.responses import Response

from app import mcp

TOOL_MODULES = [
    "tools.calculate_mumbai_transport_fare",
    "tools.fetch_station_details",
    "tools.fetch_airport_details",
    "tools.get_flight_status",
    "tools.get_traffic_conditions",
    "tools.get_penalty_details",
    "tools.get_ferry_details",
    "tools.get_local_train_status",
]

for module_name in TOOL_MODULES:
    import_module(module_name)


@mcp.custom_route(path="/", methods=["GET"])
async def root(request: Request) -> Response:
    return Response(content="MCP is running", media_type="text/plain")


app = mcp.http_app
