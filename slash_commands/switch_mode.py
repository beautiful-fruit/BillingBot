from discord import ApplicationContext, option

from bot import bot
from llm.config import AVAILABLE_MODES
from llm.llm import get_llm_service


@bot.slash_command(name="switch_mode", description="Switch between different styles of response")
@option(
    name="mode",
    description="The response style to switch to",
    choices=AVAILABLE_MODES,
    required=True
)
async def switch_mode(
    ctx: ApplicationContext,
    mode: str
):
    bot_user = bot.user
    if bot_user is None:
        await ctx.respond("Bot is not ready yet. Please try again later.")
        return

    llm_service = get_llm_service()
    llm_service.config.response_mode = mode
    await ctx.respond(f"已切換回應模式至: {mode}")
