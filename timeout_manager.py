from discord import Message

from asyncio import sleep as asleep
from dataclasses import dataclass
from datetime import datetime
try:
    from datetime import UTC
except ImportError:
    from datetime import timezone
    UTC = timezone.utc

from utils.edit_origin_message import request_timeout


@dataclass
class Data:
    uid: int
    is_borrow: bool
    message: Message


_data: dict[int, Data] = {}


def add_request(uid: int, is_borrow: bool, message: Message) -> None:
    if _data.get(uid) is not None:
        return
    _data[uid] = Data(uid, is_borrow, message)


def remove_request(uid: int) -> None:
    if _data.get(uid) is None:
        return
    _data.pop(uid)


async def task():
    while True:
        pop_list = []
        for uid, data in _data.items():
            message = data.message

            delta_time = datetime.now(UTC) - message.created_at
            if delta_time.total_seconds() > 300:
                await request_timeout(message=message, uid=uid, is_borrow=data.is_borrow)
                pop_list.append(uid)

        for uid in pop_list:
            _data.pop(uid)
        await asleep(10)
