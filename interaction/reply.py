from discord import Bot, ClientUser, Embed, EmbedAuthor, Member, Message, User
from discord.enums import ButtonStyle
from discord.ui import Button, View

from datetime import datetime
from os import getenv
from dataclasses import dataclass
from typing import Optional, Union

from db import get_db
from repository.borrow_repository import BorrowRepository
from timeout_manager import add_request
from utils.edit_origin_message import accept_or_reject_func


CHANNEL_ID = int(getenv("DISCORD_TARGET_CHANNEL_ID", "0"))
CUSTOM_ID_PREFIX = getenv("CUSTOM_ID_PREFIX", "default_prefix")

UserAlias = Union[User, Member]


@dataclass
class CheckResult():
    user: UserAlias
    bot_user: ClientUser
    content: str
    mentions: list[UserAlias]


@dataclass
class ParserResult():
    another_user: UserAlias
    borrow_from: UserAlias
    borrow_to: UserAlias
    amount: Union[int, str]


def checker(bot: Bot, message: Message) -> Optional[CheckResult]:
    user = message.author
    bot_user = bot.user

    # Check channel and user
    if message.channel.id != CHANNEL_ID or bot_user is None or user == bot_user or user.bot:
        return

    # Check format
    content = message.content
    mentions = message.mentions
    mentions_len = len(mentions)
    if "欠" not in content or mentions_len not in [1, 2]:
        return
    if mentions_len == 1 and mentions[0].id == user.id:
        return
    elif mentions_len == 2 and user.id not in [mention.id for mention in mentions]:
        return

    return CheckResult(
        user=user,
        bot_user=bot_user,
        content=content,
        mentions=mentions,
    )


def parser(
    message: Message,
    check_result: CheckResult
) -> Optional[ParserResult]:
    user = check_result.user
    content = check_result.content
    mentions = check_result.mentions

    # Parse user relationship
    split_idx = content.index("欠")
    another_user = mentions[1] if mentions[0].id == user.id else mentions[0]

    idx = content.index(another_user.mention)
    if idx < split_idx:
        borrow_to, borrow_from = another_user, user
    else:
        borrow_to, borrow_from = user, another_user

    # Parse amount position
    end_idx = split_idx + 1
    for mention_user in message.mentions:
        idx = content.index(mention_user.mention)
        if idx > end_idx:
            end_idx = idx + len(mention_user.mention)

    amount_str = content[end_idx:].strip()
    if not amount_str:
        return

    # Parse amount
    try:
        filter_amount_str = amount_str
        for c in ["元", "塊"]:
            filter_amount_str = filter_amount_str.replace(c, "")

        amount = int(filter_amount_str.strip())
        if amount == 0:
            return

        if amount < 0:
            amount = -amount
            borrow_from, borrow_to = borrow_to, borrow_from
    except ValueError:
        amount = amount_str

    return ParserResult(
        another_user=another_user,
        borrow_from=borrow_from,
        borrow_to=borrow_to,
        amount=amount,
    )


async def reply(bot: Bot, message: Message):
    check_result = checker(bot, message)
    if check_result is None:
        return

    parser_result = parser(message, check_result)
    if parser_result is None:
        return

    borrow_from = parser_result.borrow_from
    borrow_to = parser_result.borrow_to
    amount = parser_result.amount

    async with get_db() as conn:
        borrow_data = await BorrowRepository.insert(
            conn=conn,
            from_uid=borrow_from.id,
            to_uid=borrow_to.id,
            item=amount,
            url=message.jump_url,
        )
        uid = borrow_data.uid.value

    user = check_result.user
    bot_user = check_result.bot_user
    another_user = parser_result.another_user

    item_str = f"{borrow_data.amount} 元" if borrow_data.amount is not None else borrow_data.other
    embed = Embed(
        color=0xFF8800,
        title="等待確認中...",
        description=f"<@{borrow_data.to_uid}> 欠 <@{borrow_data.from_uid}> {item_str}",
        timestamp=datetime.now(),
        author=EmbedAuthor(
            name=bot_user.display_name,
            icon_url=bot_user.display_avatar.url,
        ),
        thumbnail=another_user.display_avatar.url,
    )

    if borrow_to.id == user.id:
        embed = await accept_or_reject_func(
            oper="accept",
            uid=uid,
            is_borrow=True,
            embed=embed
        )

        await message.reply(
            content="",
            embed=embed,
            view=None
        )

        return
    views = View(
        Button(
            style=ButtonStyle.green,
            label="確認",
            custom_id=f"{CUSTOM_ID_PREFIX}confirm_borrow_trgs_{another_user.id}_trge_uid_{borrow_data.uid.value}",
        ),
        Button(
            style=ButtonStyle.red,
            label="拒絕",
            custom_id=f"{CUSTOM_ID_PREFIX}reject_borrow_trgs_{another_user.id}_trge_uid_{borrow_data.uid.value}",
        ),
        store=False
    )

    reply_message = await message.reply(
        content=f"{another_user.mention} 請於 5 分鐘內確認此筆紀錄：",
        embed=embed,
        view=views
    )

    add_request(uid=uid, is_borrow=True, message=reply_message)
