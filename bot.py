from discord import (
    Bot,
    Embed,
    EmbedAuthor,
    Intents,
    Interaction,
    Message,
)
from discord.enums import ButtonStyle
from discord.ui import (
    Button,
    View
)

from datetime import datetime
try:
    from datetime import UTC
except ImportError:
    from datetime import timezone
    UTC = timezone.utc
from os import getenv

from custom_interaction.confirm_or_reject import (
    checker as confirm_or_reject_checker,
    func as confirm_or_reject_func
)
from db import get_db
from repository.borrow_repository import BorrowRepository

CHANNEL_ID = int(getenv("DISCORD_TARGET_CHANNEL_ID", "0"))
CUSTOM_ID_PREFIX = getenv("CUSTOM_ID_PREFIX", "default_prefix")

intents = Intents.default()
intents.message_content = True

bot = Bot(intents=intents)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


@bot.event
async def on_message(message: Message):
    user = message.author
    bot_user = bot.user

    if bot_user is None:
        return

    if message.channel.id != CHANNEL_ID or user == bot_user:
        return

    content = message.content
    mentions = message.mentions
    mentions_len = len(mentions)
    if "欠" not in content or mentions_len not in [1, 2]:
        return

    split_idx = content.index("欠")
    end_idx = split_idx + 1
    if mentions_len == 1:
        if mentions[0].id == user.id:
            return

        another_user = mentions[0]
    else:
        if mentions[0].id != user.id and mentions[1].id != user.id:
            return

        another_user = mentions[0] if mentions[1].id == user.id else mentions[1]

    idx = content.index(another_user.mention)
    if idx < split_idx:
        borrow_to, borrow_from = another_user, user
    else:
        borrow_to, borrow_from = user, another_user

    for mention_user in message.mentions:
        idx = content.index(mention_user.mention)
        if idx > end_idx:
            end_idx = idx + len(mention_user.mention)

    amount_str = content[end_idx:].strip()
    if not amount_str:
        return

    try:
        amount = int(amount_str)
        if amount < 0:
            amount = -amount
            borrow_from, borrow_to = borrow_to, borrow_from

        if amount == 0:
            return
    except ValueError:
        amount = None

    async with get_db() as conn:
        borrow_data = await BorrowRepository.insert(
            conn=conn,
            from_uid=borrow_from.id,
            to_uid=borrow_to.id,
            item=amount or amount_str,
            url=message.jump_url,
        )

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

    await message.reply(
        content=f"{another_user.mention} 請於 5 分鐘內確認此筆紀錄：",
        embed=embed,
        view=views
    )


@bot.event
async def on_interaction(interaction: Interaction):
    if await confirm_or_reject_checker(bot, interaction):
        await confirm_or_reject_func(bot, interaction)
        return

    await bot.process_application_commands(interaction)


async def start():
    token = getenv("DISCORD_BOT_TOKEN", None)
    if token is None:
        raise ValueError(
            "DISCORD_BOT_TOKEN is not set in environment variables.")

    await bot.start(token=token)
