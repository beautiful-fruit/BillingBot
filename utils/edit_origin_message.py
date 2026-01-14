from discord import Message

from db import get_db
from repository.borrow_repository import BorrowRepository
from repository.return_repository import ReturnRepository


async def request_timeout(message: Message, uid: int, is_borrow: bool):
    async with get_db() as conn:
        if is_borrow:
            await BorrowRepository.delete_by_uid(conn=conn, uid=uid)
        else:
            await ReturnRepository.delete_by_uid(conn=conn, uid=uid)

    if len(message.embeds) == 0:
        return
    embed = message.embeds[0]
    embed.color = 0x888888
    embed.title = "操作已過期"

    await message.edit(
        content="",
        embed=embed,
        view=None
    )

    return


async def request_accept(message: Message, uid: int, is_borrow: bool):
    async with get_db() as conn:
        if is_borrow:
            await BorrowRepository.set_pending_by_uid(
                conn=conn,
                uid=uid,
                pending=False
            )
        else:
            await ReturnRepository.delete_by_uid(
                conn=conn,
                uid=uid
            )

    if len(message.embeds) == 0:
        return
    embed = message.embeds[0]
    embed.color = 0x00FF00
    embed.title = "操作已完成"

    await message.edit(
        content="",
        embed=embed,
        view=None
    )

    return


async def request_reject(message: Message, uid: int, is_borrow: bool):
    async with get_db() as conn:
        if is_borrow:
            await BorrowRepository.delete_by_uid(conn=conn, uid=uid)
        else:
            await ReturnRepository.delete_by_uid(conn=conn, uid=uid)

    if len(message.embeds) == 0:
        return
    embed = message.embeds[0]
    embed.color = 0xFF0000
    embed.title = "操作已拒絕"

    await message.edit(
        content="",
        embed=embed,
        view=None
    )

    return
