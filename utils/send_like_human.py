from discord import TextChannel, Thread

from asyncio import sleep as asleep
from random import random
from typing import Union


async def send_like_human(
    channel: Union[TextChannel, Thread],
    content: str
) -> None:
    message_list = content.split("\n\n")
    for i, msg in enumerate(message_list):
        await channel.send(msg)

        if i >= len(message_list) - 1:
            break

        async with channel.typing():
            await asleep(random() + 0.3)
