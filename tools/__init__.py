from .base import ToolBase
from .discord_tool import DiscordTools
from .timer_tool import TimerTools

__all__ = [
    "ToolBase",
    "DiscordTools",
    "TimerTools",
    "AVAILABLE_TOOLS"
]

AVAILABLE_TOOLS: list[type[ToolBase]] = [
    DiscordTools,
    TimerTools,
]
