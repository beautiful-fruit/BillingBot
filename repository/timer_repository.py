from asyncpg import Connection

from datetime import datetime
try:
    from datetime import UTC
except ImportError:
    from datetime import timezone
    UTC = timezone.utc
from typing import Optional

from schemas.timers import TimerData


class TimerRepository:
    @staticmethod
    async def insert(
        conn: Connection,
        channel_id: int,
        user_id: int,
        trigger_time: int,
        message: str,
        origin_message: str,
    ) -> TimerData:
        data = TimerData(
            channel_id=channel_id,
            user_id=user_id,
            trigger_time=datetime.fromtimestamp(trigger_time, UTC),
            message=message,
            original_message=origin_message,
        )

        cmd, params = data.insert_query
        await conn.execute(cmd, *params)

        return data

    @staticmethod
    async def get_all_timers(conn: Connection) -> list[TimerData]:
        rows = await conn.fetch("""
            SELECT id, channel_id, user_id, trigger_time, message, original_message
            FROM timers
            ORDER BY trigger_time ASC
        """)

        return [
            TimerData(
                id=row["id"],
                channel_id=row["channel_id"],
                user_id=row["user_id"],
                trigger_time=row["trigger_time"],
                message=row["message"],
                original_message=row["message"],
            ) for row in rows
        ]

    @staticmethod
    async def get_timers_by_channel_id(
        conn: Connection,
        channel_id: int,
        user_id: Optional[int] = None,
    ) -> list[TimerData]:
        rows = await conn.fetch("""
            SELECT id, channel_id, user_id, trigger_time, message, original_message
            FROM timers
            WHERE channel_id = $1 AND ($2::bigint IS NULL OR user_id = $2)
            ORDER BY trigger_time ASC
        """, channel_id, user_id)

        return [
            TimerData(
                id=row["id"],
                channel_id=row["channel_id"],
                user_id=row["user_id"],
                trigger_time=row["trigger_time"],
                message=row["message"],
                original_message=row["original_message"],
            ) for row in rows
        ]

    @staticmethod
    async def get_timer_by_id(
        conn: Connection,
        channel_id: int,
        timer_id: int,
    ) -> Optional[TimerData]:
        row = await conn.fetchrow("""
            SELECT id, channel_id, user_id, trigger_time, message, original_message
            FROM timers
            WHERE id = $1 AND channel_id = $2
        """, timer_id, channel_id)

        if not row:
            return None

        return TimerData(
            id=row["id"],
            channel_id=row["channel_id"],
            user_id=row["user_id"],
            trigger_time=row["trigger_time"],
            message=row["message"],
            original_message=row["original_message"],
        )

    @staticmethod
    async def delete_timer_by_id(
        conn: Connection,
        channel_id: int,
        timer_id: int,
    ) -> None:
        await conn.execute("""
            DELETE FROM timers
            WHERE id = $1 AND channel_id = $2
        """, timer_id, channel_id)

    @staticmethod
    async def update_timer_trigger_time(
        conn: Connection,
        channel_id: int,
        timer_id: int,
        new_trigger_time: int,
    ) -> None:
        await conn.execute("""
            UPDATE timers
            SET trigger_time = $1
            WHERE id = $2 AND channel_id = $3
        """, datetime.fromtimestamp(new_trigger_time, UTC), timer_id, channel_id)

    @staticmethod
    async def update_timer_message(
        conn: Connection,
        channel_id: int,
        timer_id: int,
        new_message: str,
    ) -> None:
        await conn.execute("""
            UPDATE timers
            SET message = $1
            WHERE id = $2 AND channel_id = $3
        """, new_message, timer_id, channel_id)
