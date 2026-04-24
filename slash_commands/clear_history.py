from discord import ApplicationContext

from bot import bot
from db import get_db
from repository.chat_repository import ChatRepository


@bot.slash_command(name="clear", description="Clear Deepseek chat history")
async def clear_history(ctx: ApplicationContext):
    bot_user = bot.user
    if bot_user is None:
        await ctx.respond("Bot is not ready yet. Please try again later.")
        return

    channel = ctx.channel
    if channel is None:
        await ctx.respond("This command can only be used in a channel.")
        return

    async with get_db() as conn:
        await ChatRepository.clear_channel_history(
            conn=conn,
            channel_id=channel.id
        )

    await ctx.respond("已清除此頻道的對話歷史。")
