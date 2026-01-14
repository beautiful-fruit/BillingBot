from asyncpg import Connection

from typing import Union

from schemas.borrow_data import Borrow


class BorrowRepository:
    @staticmethod
    async def insert(
        conn: Connection,
        from_uid: int,
        to_uid: int,
        item: Union[int, str],
        url: str
    ) -> Borrow:
        data = Borrow(
            from_uid=from_uid,
            to_uid=to_uid,
            amount=item if isinstance(item, int) else None,
            other=item if isinstance(item, str) else None,
            url=url,
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
            DELETE FROM borrow_history
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
            UPDATE borrow_history
            SET pending = $1
            WHERE uid = $2
            """,
            pending,
            uid
        )
