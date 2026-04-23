from asyncpg import Connection
from typing import List, Optional
from pydantic_snowflake import SnowflakeId

from schemas.chat_message import ChatMessage, ChatRoleName


class ChatRepository:
    @staticmethod
    async def insert(
        conn: Connection,
        channel_id: int,
        role: ChatRoleName,
        content: str,
        user_id: Optional[int] = None,
        username: Optional[str] = None,
        message_id: Optional[int] = None
    ) -> ChatMessage:
        data = ChatMessage(
            channel_id=channel_id,
            user_id=user_id,
            username=username,
            role=role,
            content=content,
            message_id=message_id
        )

        cmd, params = data.insert_query
        await conn.execute(cmd, *params)

        return data

    @staticmethod
    async def get_channel_history(
        conn: Connection,
        channel_id: int,
        limit: int = 20
    ) -> List[ChatMessage]:
        rows = await conn.fetch("""
            SELECT id, channel_id, user_id, username, role, content, message_id
            FROM chat_messages
            WHERE channel_id = $1
            ORDER BY id DESC
            LIMIT $2
        """, channel_id, limit)

        return sorted([
            ChatMessage(
                id=SnowflakeId(row["id"]),
                channel_id=row["channel_id"],
                user_id=row["user_id"],
                username=row["username"],
                role=row["role"],
                content=row["content"],
                message_id=row["message_id"]
            ) for row in rows
        ], key=lambda x: x.id.value)

    @staticmethod
    async def delete_old_messages(
        conn: Connection,
        channel_id: int,
        percentage: float = 0.15
    ) -> None:
        # 先取得該頻道的總訊息數
        count_result = await conn.fetchval("""
            SELECT COUNT(*) FROM chat_messages
            WHERE channel_id = $1
        """, channel_id)

        if count_result is None or count_result <= 10:  # 如果訊息少於10條，不刪除
            return

        # 計算要刪除的數量（前15%）
        delete_count = int(count_result * percentage)

        if delete_count < 1:  # 如果計算結果小於1，至少刪除1條
            delete_count = 1

        # 刪除最舊的訊息
        await conn.execute("""
            DELETE FROM chat_messages
            WHERE id IN (
                SELECT id
                FROM chat_messages
                WHERE channel_id = $1
                ORDER BY id ASC
                LIMIT $2
            )
        """, channel_id, delete_count)

    @staticmethod
    async def clear_channel_history(
        conn: Connection,
        channel_id: int
    ) -> None:
        await conn.execute("""
            DELETE FROM chat_messages
            WHERE channel_id = $1
        """, channel_id)
