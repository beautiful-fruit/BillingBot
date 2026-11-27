from discord import (
    ApplicationContext,
    DiscordException,
    Embed,
    EmbedAuthor,
    EmbedField,
    File,
)

from asyncio import gather, to_thread
from datetime import datetime

from bot import bot
from db import get_db
from repository.summary_repository import SummaryRepository
from utils.debt_graph import render_debt_graph
from utils.debt_planner import Transfer, plan_settlement

# Discord embed field value 上限
MAX_FIELD_VALUE = 1024
AVATAR_SIZE = 128
GRAPH_FILENAME = "debt_graph.png"


async def _fetch_avatar(ctx: ApplicationContext, uid: int) -> bytes | None:
    try:
        user = (
            (ctx.guild.get_member(uid) if ctx.guild else None)
            or bot.get_user(uid)
            or await bot.fetch_user(uid)
        )
        asset = user.display_avatar.with_size(AVATAR_SIZE).with_static_format("png")
        return await asset.read()
    except DiscordException:
        return None


async def _build_graph(ctx: ApplicationContext, transfers: list[Transfer]) -> File:
    uids = sorted({uid for t in transfers for uid in (t.payer, t.payee)})
    avatar_list = await gather(*(_fetch_avatar(ctx, uid) for uid in uids))
    avatars = dict(zip(uids, avatar_list))
    image = await to_thread(render_debt_graph, transfers, avatars)
    return File(image, filename=GRAPH_FILENAME)


@bot.slash_command(
    name="simplify",
    description="規劃債務網路整理方案（僅預覽，不會修改任何資料）",
)
async def simplify_cmd(ctx: ApplicationContext):
    bot_user = bot.user
    if bot_user is None:
        await ctx.respond("Bot is not ready yet. Please try again later.")
        return

    # 抓取頭像與繪圖可能超過 3 秒，先 defer 避免 interaction 逾時
    await ctx.defer()

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

    if not transfers:
        await ctx.respond(embed=embed)
        return

    embed.set_image(url=f"attachment://{GRAPH_FILENAME}")
    await ctx.respond(embed=embed, file=await _build_graph(ctx, transfers))
