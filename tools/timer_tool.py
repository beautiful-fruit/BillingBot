from asyncio import gather, get_running_loop, sleep as asleep, Task
from discord import Bot, Message, TextChannel
from orjson import dumps

from datetime import datetime, timedelta
try:
    from datetime import UTC
except ImportError:
    from datetime import timezone
    UTC = timezone.utc
from typing import Annotated, Awaitable, Callable, Optional

from db import get_db
from repository.timer_repository import TimerRepository
from schemas.timers import TimerData
from tools.base import SystemEventCallback

from .base import ToolBase


def _timer_to_dict(timer: TimerData) -> dict:
    return {
        "id": str(timer.id),
        "trigger_time": timer.trigger_time.astimezone().isoformat(),
        "message": timer.message,
        "original_message": {
            "author_id": str(timer.user_id),
            "content": timer.original_message,
            "created_at": timer.id.datetime.astimezone().isoformat(),
        }
    }


class TimerTrigger():
    system_event_callback: SystemEventCallback
    _bot: Bot
    _timers: list[TimerData]
    _check_task: Optional[Task]

    def __init__(self, bot: Bot, system_event_callback: SystemEventCallback) -> None:
        self._bot = bot
        self.system_event_callback = system_event_callback
        self._timers = []
        self._check_task = None

    async def refresh(self) -> None:
        async with get_db() as conn:
            db_timers = await TimerRepository.get_all_timers(conn)
        self._timers = db_timers

    async def _check_timers(self) -> None:
        await self.refresh()
        while True:
            current_time = datetime.now(UTC)

            removed_timers: list[TimerData] = []
            const_timers = [timer for timer in self._timers]
            print(const_timers, self._timers)
            for timer in const_timers:
                print(f"Checking Timer: {timer.id} (Trigger Time: {timer.trigger_time.astimezone(UTC).isoformat()}, Current Time: {current_time.astimezone(UTC).isoformat()})")
                if timer.trigger_time.astimezone(UTC) > current_time:
                    continue

                channel = self._bot.get_channel(timer.channel_id) or await self._bot.fetch_channel(timer.channel_id)
                if not channel:
                    removed_timers.append(timer)
                    continue

                print(timer)
                print("Convert result", _timer_to_dict(timer))
                print(dumps(_timer_to_dict(timer)).decode('utf-8'))
                message = dumps(_timer_to_dict(timer=timer)).decode('utf-8')
                print(f"Timer Triggered: {timer.id} (Channel: {channel}, Message: {message})")
                await self.system_event_callback(
                    f"[Timer Triggered]: {message}",
                    channel,  # type: ignore
                )

                removed_timers.append(timer)

            for timer in removed_timers:
                self._timers.remove(timer)

            async with get_db() as conn:
                await gather(*[
                    TimerRepository.delete_timer_by_id(
                        conn=conn,
                        channel_id=timer.channel_id,
                        timer_id=int(timer.id)
                    )
                    for timer in removed_timers
                ])

            await asleep(5)

    async def setup(self):
        if self._check_task is None or self._check_task.done():
            self._check_task = get_running_loop().create_task(self._check_timers())


class TimerTools(ToolBase):
    class_name = "timer"
    description = """
提供計時器相關功能，包括查看、添加、更新和刪除計時器。當計時器觸發時，會在對應的頻道發送一條消息，內容為計時器訊息和創建者的資訊。
如果使用者要求你在一段時間後提醒他們某件事，你可以使用這個工具來創建一個計時器。
例如，如果使用者說「請在 10 分鐘後提醒我喝水」，你可以使用這個工具來創建一個計時器。
其中的 message 參數可以包含任何文本內容，使用者不會看到這些內容，這個文本是提供給你的，當計時器觸發時，你會收到這個文本內容，讓你知道該做什麼。
例如，你設置了一個計時器，message 參數為「提醒 <@user_id> 喝水」，當計時器觸發時，你會收到這個文本內容，讓你知道該做什麼。
當計時器觸發時，會由伺服器主動發一條消息給你，內容為「[Timer Triggered][Created by <@user_id>]: 提醒 <@user_id> 喝水」。
記住，message 的文本不是給使用者看的，而是給你的，當計時器觸發時，你會收到這個文本內容，讓你知道該做什麼。
當你收到由 system role 發出的 [Timer Triggered][Created by <@user_id>] 消息時，這意味著計時器已經觸發，你應該根據 message 參數的內容來執行相應的操作，而不是重新創建一個新的計時器，除非使用者再次要求你在未來的某個時間點提醒他們。
此外，trigger_time 參數是預計觸發的時間，例如使用者要你在 10 分鐘後提醒他們，你需要將當前時間加上 10 分鐘，然後將結果作為 trigger_time 參數的值。
**不要在 trigger_time 放入現在的時間**，你可以透過 calculate_timestamp 工具來計算 trigger_time 的值，這個工具會接受從現在起的秒數、分鐘數、小時數和天數，然後返回一個 Unix Timestamp，這個 Timestamp 就可以用作 trigger_time 的值。
計時器不會發送給使用者任何消息，當計時器觸發時，只有你會收到一條消息，內容為「[Timer Triggered][Created by <@user_id>]: {message}」，其中 {message} 是你在創建計時器時提供的 message 參數的內容。
你需要根據你所留下的 message 參數的內容來執行相應的操作，例如如果 message 是「提醒 <@user_id> 喝水」，當你收到計時器觸發的消息時，你應該在對應的頻道發送一條消息，內容為「<@user_id>，該喝水了！」。
"""

    @classmethod
    async def setup(cls, bot: Bot, system_event_callback: Callable[[str, TextChannel], Awaitable[None]]) -> None:
        global _timer_trigger
        await super().setup(bot, system_event_callback)

        if _timer_trigger is None:
            _timer_trigger = TimerTrigger(
                bot=bot,
                system_event_callback=system_event_callback
            )
            await _timer_trigger.setup()

        return


_timer_trigger: Optional[TimerTrigger] = None


@TimerTools.register(description="查看所有計時器")
async def view_timers(
    channel: TextChannel,
) -> list[dict]:
    async with get_db() as conn:
        timers = await TimerRepository.get_timers_by_channel_id(
            conn=conn,
            channel_id=channel.id
        )

    if not timers:
        return []

    return [
        _timer_to_dict(timer)
        for timer in timers
    ]


@TimerTools.register(description="計算時間戳")
async def calculate_timestamp(
    seconds: Annotated[int, "從現在起的秒數"] = 0,
    minutes: Annotated[int, "從現在起的分鐘數"] = 0,
    hours: Annotated[int, "從現在起的小時數"] = 0,
    days: Annotated[int, "從現在起的天數"] = 0,
) -> dict:
    now = datetime.now(UTC)
    delta = timedelta(
        seconds=seconds,
        minutes=minutes,
        hours=hours,
        days=days,
    )
    target_time = now + delta

    return {
        "timestamp": int(target_time.timestamp()),
        "iso_time": target_time.astimezone().isoformat(),
    }


@TimerTools.register(description="新增一個計時器")
async def add_timer(
    channel: TextChannel,
    user_id: Annotated[str, "Discord 使用者 ID"],
    trigger_time: Annotated[int, "觸發時間，Unix Timestamp"],
    message: Annotated[str, "計時器訊息內容"],
    origin_message: Optional[Message] = None,
) -> dict:
    if origin_message is None:
        return {"error": "Origin message is required to create a timer."}

    try:
        async with get_db() as conn:
            timer = await TimerRepository.insert(
                conn=conn,
                channel_id=channel.id,
                user_id=int(user_id),
                trigger_time=trigger_time,
                message=message,
                origin_message=origin_message.content,
            )
    except ValueError:
        return {"error": "Invalid trigger_time. Please provide a valid Unix timestamp."}

    if _timer_trigger is not None:
        await _timer_trigger.refresh()

    return {
        "message": "Timer added successfully",
        "timer": _timer_to_dict(timer)
    }


@TimerTools.register(description="通過計時器 ID 獲得計時器")
async def get_timer_by_id(
    channel: TextChannel,
    timer_id: Annotated[str, "計時器 ID"],
) -> dict:
    async with get_db() as conn:
        timer = await TimerRepository.get_timer_by_id(
            conn=conn,
            channel_id=channel.id,
            timer_id=int(timer_id)
        )

    return _timer_to_dict(timer) if timer else {}


@TimerTools.register(description="通過計時器 ID 刪除計時器")
async def delete_timer_by_id(
    channel: TextChannel,
    timer_id: Annotated[str, "計時器 ID"],
) -> dict:
    async with get_db() as conn:
        await TimerRepository.delete_timer_by_id(
            conn=conn,
            channel_id=channel.id,
            timer_id=int(timer_id)
        )

    if _timer_trigger is not None:
        await _timer_trigger.refresh()

    return {"message": "Timer deleted successfully"}


@TimerTools.register(description="通過計時器 ID 更新計時器觸發時間")
async def update_timer_trigger_time(
    channel: TextChannel,
    timer_id: Annotated[str, "計時器 ID"],
    new_trigger_time: Annotated[int, "新的觸發時間，Unix Timestamp"],
) -> dict:
    try:
        async with get_db() as conn:
            await TimerRepository.update_timer_trigger_time(
                conn=conn,
                channel_id=channel.id,
                timer_id=int(timer_id),
                new_trigger_time=new_trigger_time
            )
    except ValueError:
        return {"error": "Invalid new_trigger_time. Please provide a valid Unix timestamp."}

    if _timer_trigger is not None:
        await _timer_trigger.refresh()

    return {"message": "Timer trigger time updated successfully"}


@TimerTools.register(description="通過計時器 ID 更新計時器訊息內容")
async def update_timer_message(
    channel: TextChannel,
    timer_id: Annotated[str, "計時器 ID"],
    new_message: Annotated[str, "新的計時器訊息內容"],
) -> dict:
    async with get_db() as conn:
        await TimerRepository.update_timer_message(
            conn=conn,
            channel_id=channel.id,
            timer_id=int(timer_id),
            new_message=new_message
        )

    if _timer_trigger is not None:
        await _timer_trigger.refresh()

    return {"message": "Timer message updated successfully"}
