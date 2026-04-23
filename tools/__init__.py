from .base import ToolBase
from .discord_tool import DiscordTools

__all__ = [
    "ToolBase",
    "DiscordTools",
    "AVAILABLE_TOOLS"
]

AVAILABLE_TOOLS: list[type[ToolBase]] = [
    DiscordTools
]
