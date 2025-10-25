from starlette.requests import Request
from starlette.responses import Response

from app import mcp

from tools.greet import hello


@mcp.custom_route(path="/", methods=["GET"])
async def root(request: Request) -> Response:
    return Response(content="MCP is running", media_type="text/plain")


app = mcp.http_app
