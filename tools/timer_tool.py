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

_timer_trigger: Optional["TimerTrigger"] = None  # pylint: disable=invalid-name


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
            const_timers = self._timers.copy()
            for timer in const_timers:
                if timer.trigger_time.astimezone(UTC) > current_time:
                    continue

                channel = self._bot.get_channel(timer.channel_id) \
                    or await self._bot.fetch_channel(timer.channel_id)
                if not channel:
                    removed_timers.append(timer)
                    continue

                message = dumps(_timer_to_dict(timer=timer)).decode('utf-8')
                await self.system_event_callback(
                    f"[Timer Triggered]: {timer.message} ({message})",
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
## 工具描述
提供計時器相關功能，包括查看、添加、更新和刪除計時器。當計時器觸發時，會在對應的頻道發送一條消息，內容為計時器訊息和創建者的資訊。
如果使用者要求你在一段時間後提醒他們某件事，你可以使用這個工具來創建一個計時器。
例如，如果使用者說「請在 10 分鐘後提醒我喝水」，你可以使用這個工具來創建一個計時器。

## 參數說明：
- message: 這是計時器的訊息內容，當計時器觸發時，你會收到這個訊息內容，讓你知道該做什麼。這個訊息內容是由你自己定義的，當你創建計時器時，你需要提供這個訊息內容，當計時器觸發時，你會收到這個訊息內容，讓你知道該做什麼。
- trigger_time: 這是計時器的觸發時間，當時間到達時便會觸發計時器，你需要提供一個 Unix Timestamp 作為這個參數的值，你可以使用 calculate_timestamp 工具來計算這個 Unix Timestamp 的值，當計時器觸發時，你會收到這個觸發時間的資訊，讓你知道該做什麼。

## 如何使用：
1. 當使用者要求你在一段時間後提醒他們某件事時，使用 add_timer 工具來創建一個計時器，提供 message 和 trigger_time 參數的值。
2. 等待計時器觸發，當時間到達時，你會收到一條 system 的消息，內容為計時器訊息和創建者的資訊，讓你知道該做什麼。
3. 請你根據你收到的計時器訊息來執行相應的操作，例如提醒使用者該做什麼，或者在頻道中發送一條消息等等。
4. 當你收到計時器觸發的消息後，你應該根據你先前留下的 message 來執行相應的操作，而不是再創建一個新的計時器。
5. 使用者可能會有許多時間點需要你提醒，如果使用者提出更多的請求，你就要建立對應的計時器。
6. 如果你不確定該怎麼回應使用者的請求來創建計時器，你可以詢問使用者更多的細節，例如他們想要在什麼時間點被提醒，或者他們想要被提醒什麼內容等等，然後根據使用者提供的資訊來創建計時器。
7. 如果你不確定計時器是否已經存在了，你可以使用 view_timers 工具來查看目前頻道中有哪些計時器，這樣你就不會創建重複的計時器了。
8. 如果計時器不存在的話，你就要建立一個新的計時器，這樣當時間到達時，你就會收到計時器觸發的消息了。

## 正確示範：
User: 請在 10 分鐘後提醒我喝水
Assistant: 好的，我已經幫你設置了一個計時器，當時間到達時，我會提醒你喝水。
    - 透過 calculate_timestamp 工具來計算出 10 分鐘後的 Unix Timestamp。
    - 呼叫 add_timer 工具，提供 message 和 trigger_time 參數的值來創建計時器。
...
(10 分鐘後)
...
System: [Timer Triggered]: 喝水 (<計時器資料>)
Assistant: 喝水時間到了！請記得喝水哦！
    - 根據收到的計時器訊息來執行相應的操作，例如提醒使用者該做什麼，或者在頻道中發送一條消息等等。
    - **不要**再創建一個新的計時器，因為這樣會導致無限循環。
    - 你應該執行相應的操作來回應這個計時器觸發的消息，而不是告訴使用者你已經創建了一個新的計時器，這樣會導致無限循環。

## 錯誤示範：
User: 請在 10 分鐘後提醒我喝水
Assistant: 好的，我已經幫你設置了一個計時器，當時間到達時，我會提醒你喝水。
...
(10 分鐘後)
...
System: [Timer Triggered]: 喝水 (<計時器資料>)
Assistant: 好的，我已經幫你設置了一個計時器，當時間到達時，我會提醒你喝水。
    - **錯誤**：這樣的回應會導致無限循環，因為每次計時器觸發時，你都創建了一個新的計時器，這樣就會一直下去，直到系統崩潰。
    - 你應該執行相應的操作來回應這個計時器觸發的消息，而不是告訴使用者你已經創建了一個新的計時器，這樣會導致無限循環。

## 注意事項：
- 當你創建一個計時器時，請確保提供的 trigger_time 是一個有效的 Unix Timestamp，否則計時器將無法正常工作。
- 當計時器觸發時，你會收到一條 system 的消息，內容為計時器訊息和創建者的資訊，請你根據這些資訊來執行相應的操作，而不是再創建一個新的計時器，這樣會導致無限循環。
- 使用者不會收到 message 參數的值，這個參數只是用來讓你在計時器觸發時知道該做什麼，請你根據這個參數的值來執行相應的操作。
- 你應該留下明確的 message 內容，這樣當計時器觸發時，你就知道該做什麼。
- 計時器的觸發會以 system prompt 的形式發送，因此你收到的訊息清單的最後一條消息會是由你自己發出的而不是使用者發出的，請你不要重複回應使用者的要求來創建新的計時器，這樣會導致無限循環。
"""

    @classmethod
    async def setup(
        cls,
        bot: Bot,
        system_event_callback: Callable[[str, TextChannel], Awaitable[None]]
    ) -> None:
        global _timer_trigger  # pylint: disable=global-statement
        await super().setup(bot, system_event_callback)

        if _timer_trigger is None:
            _timer_trigger = TimerTrigger(
                bot=bot,
                system_event_callback=system_event_callback
            )
            await _timer_trigger.setup()

        return


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


@TimerTools.register(description="新增一個計時器", enable_in_system_event=False)
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
