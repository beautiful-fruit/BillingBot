from discord import ApplicationContext, Embed, EmbedAuthor, EmbedField

from datetime import datetime

from bot import bot
from db import get_db
from repository.summary_repository import SummaryRepository


@bot.slash_command(name="summary", description="Get summary of debts")
async def summary(ctx: ApplicationContext):
    user = ctx.author
    bot_user = bot.user
    if bot_user is None:
        await ctx.respond("Bot is not ready yet. Please try again later.")
        return

    async with get_db() as conn:
        summary_data = await SummaryRepository.get_by_user_id(conn=conn, user_id=user.id)

    borrow_from: list[tuple[int, int]] = []
    borrow_to: list[tuple[int, int]] = []
    for key, summary in summary_data.items():
        if summary.user1 == user.id:
            if summary.amount >= 0:
                borrow_to.append((key, summary.amount))
            else:
                borrow_from.append((key, -summary.amount))
        else:
            if summary.amount >= 0:
                borrow_from.append((key, summary.amount))
            else:
                borrow_to.append((key, -summary.amount))

    embed = Embed(
        color=0x0088FF,
        title="債務總覽",
        description="以下是您的債務總覽：",
        timestamp=datetime.now(),
        author=EmbedAuthor(
            name=bot_user.display_name,
            icon_url=bot_user.display_avatar.url,
        ),
        thumbnail=user.display_avatar.url,
        fields=[
            EmbedField(
                name="你還欠...",
                value="\n".join(
                    f"<@{uid}>: {amount} 元" for uid, amount in borrow_from
                ) or "你沒有欠別人錢🎉",
            ),
            EmbedField(
                name="有人還欠你...",
                value="\n".join(
                    f"<@{uid}>: {amount} 元" for uid, amount in borrow_to
                ) or "沒有人欠你錢💸",
            )
        ]
    )

    await ctx.respond(embed=embed)
