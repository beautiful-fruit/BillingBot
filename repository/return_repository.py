from asyncpg import Connection

from schemas.return_data import Return


class ReturnRepository:
    @staticmethod
    async def insert(
        conn: Connection,
        from_uid: int,
        to_uid: int,
        amount: int,
    ) -> Return:
        data = Return(
            from_uid=from_uid,
            to_uid=to_uid,
            amount=amount,
        )

        cmd, params = data.insert_query
        await conn.execute(cmd, *params)

        return data

    @staticmethod
    async def delete_by_uid(
        conn: Connection,
        uid: int
    ) -> None:
        await conn.execute(
            """
            DELETE FROM return_history
            WHERE uid = $1
            """,
            uid
        )

    @staticmethod
    async def set_pending_by_uid(
        conn: Connection,
        uid: int,
        pending: bool
    ) -> None:
        await conn.execute(
            """
            UPDATE return_history
            SET pending = $1
            WHERE uid = $2
            """,
            pending,
            uid
        )
