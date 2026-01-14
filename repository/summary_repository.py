from asyncpg import Connection

from schemas.summary_data import Summary


class SummaryRepository:
    @staticmethod
    async def get_by_user_id(conn: Connection, user_id: int) -> dict[int, Summary]:
        rows = await conn.fetch(
            """
            SELECT user1, user2, amount FROM summary
            WHERE user1 = $1 OR user2 = $1
            """,
            user_id,
        )

        return {
            user1 if user2 == user_id else user2:  Summary(
                user1=user1,
                user2=user2,
                amount=amount,
            )
            for user1, user2, amount in rows
        }
