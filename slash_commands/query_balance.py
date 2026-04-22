from aiohttp import ClientSession
from discord import ApplicationContext, Embed, EmbedAuthor, EmbedField

from os import getenv

from bot import bot
from db import get_db
from repository.summary_repository import SummaryRepository


@bot.slash_command(name="balance", description="Get Deepseek balance")
async def get_balance(ctx: ApplicationContext):
    user = ctx.author
    bot_user = bot.user
    if bot_user is None:
        await ctx.respond("Bot is not ready yet. Please try again later.")
        return

    model = getenv("OPENAI_MODEL", "")
    if not model.startswith("deepseek-"):
        await ctx.respond("The balance command is only available for Deepseek models.")
        return

    async with ClientSession(headers={
        "Authorization": f"Bearer {getenv('OPENAI_API_KEY', '')}"
    }) as session:
        async with session.get("https://api.deepseek.com/user/balance") as resp:
            if resp.status != 200:
                await ctx.respond("Failed to fetch balance from Deepseek API.")
                return
            data = await resp.json()

    balance: list[dict] = data.get("balance_infos", [])
    if not balance:
        await ctx.respond("No balance information available.")
        return

    message = "\n".join(
        f"{item['total_balance']} {item['currency']}"
        for item in balance
    )
    await ctx.respond(message)
