from typing import Optional
from app import mcp


@mcp.tool
async def hello(name: Optional[str] = "World") -> dict:
    """
    Returns a greeting message.

    Args:
        name (Optional[str]): The name to greet. Defaults to "World".

    Returns:
        dict: A dictionary containing the greeting message.
    """
    return {"message": "Hello, {}!".format(name or "World")}
