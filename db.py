from asyncpg import create_pool, Pool, Connection

from contextlib import asynccontextmanager
from os import getenv
from typing import AsyncGenerator

_pool = None


async def create_tables(conn: Connection) -> None:
    # Create tables if they do not exist
    with open("sql/create_tables.sql", "r", encoding="utf-8") as f:
        sql_commands = f.read()
        await conn.execute(sql_commands)

    # Create indexes if they do not exist
    with open("sql/create_indexes.sql", "r", encoding="utf-8") as f:
        sql_commands = f.read()
        await conn.execute(sql_commands)

    # Create triggers to ensure users exist
    with open("sql/trigger_check_user_exists.sql", "r", encoding="utf-8") as f:
        sql_commands = f.read()
        await conn.execute(sql_commands)

    # Create triggers to update summary table
    with open("sql/trigger_update_summary.sql", "r", encoding="utf-8") as f:
        sql_commands = f.read()
        await conn.execute(sql_commands)


@asynccontextmanager
async def init_db() -> AsyncGenerator[Pool, None]:
    global _pool
    if _pool:
        raise RuntimeError("Database pool is already initialized.")
    dsn = getenv(
        "POSTGRES_DB_URL",
        "postgresql://billing:billing@localhost:5432/billing"
    )
    min_size = int(getenv("POSTGRES_POOL_MIN_SIZE", "10"))
    max_size = int(getenv("POSTGRES_POOL_MAX_SIZE", min_size))

    pool = await create_pool(
        dsn=dsn,
        min_size=min_size,
        max_size=max_size,
    )

    try:
        _pool = pool
        async with pool.acquire() as conn:
            await create_tables(conn)  # type: ignore
        yield pool
    finally:
        await pool.close()
        _pool = None


@asynccontextmanager
async def get_db(transaction: bool = False) -> AsyncGenerator[Connection, None]:
    if _pool is None:
        raise RuntimeError("Database pool is not initialized.")

    async with _pool.acquire() as conn:
        if transaction:
            async with conn.transaction():
                yield conn  # type: ignore
        else:
            yield conn  # type: ignore
