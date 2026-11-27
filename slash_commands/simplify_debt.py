from discord import ApplicationContext, Embed, EmbedAuthor, EmbedField

from datetime import datetime

from bot import bot
from db import get_db
from repository.summary_repository import SummaryRepository
from utils.debt_planner import plan_settlement

# Discord embed field value 上限
MAX_FIELD_VALUE = 1024


@bot.slash_command(
    name="simplify",
    description="規劃債務網路整理方案（僅預覽，不會修改任何資料）",
)
async def simplify_cmd(ctx: ApplicationContext):
    bot_user = bot.user
    if bot_user is None:
        await ctx.respond("Bot is not ready yet. Please try again later.")
        return

    # 僅進行讀取：以 read-only transaction 在資料庫層級保證不會有任何寫入
    async with get_db() as conn:
        async with conn.transaction(readonly=True):
            summaries = await SummaryRepository.get_all_nonzero(conn=conn)

    transfers = plan_settlement(summaries)

    lines: list[str] = []
    for t in transfers:
        line = f"<@{t.payer}> 欠 <@{t.payee}> {t.amount} 元"
        if len("\n".join(lines + [line, "…"])) > MAX_FIELD_VALUE:
            lines.append("…")
            break
        lines.append(line)

    embed = Embed(
        color=0x0088FF,
        title="債務整理規劃",
        description="以下是整理後的債務關係（僅為規劃，尚未套用）：",
        timestamp=datetime.now(),
        author=EmbedAuthor(
            name=bot_user.display_name,
            icon_url=bot_user.display_avatar.url,
        ),
        fields=[
            EmbedField(
                name="整理後...",
                value="\n".join(lines) or "目前沒有需要整理的債務🎉",
            )
        ]
    )

    await ctx.respond(embed=embed)
