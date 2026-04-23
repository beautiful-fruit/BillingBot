from discord import (
    Bot,
    Intents,
    Interaction,
    Message,
)

from fun import fun
from os import getenv

from interaction.confirm_or_reject import (
    checker as confirm_or_reject_checker,
    func as confirm_or_reject_func
)
from interaction.reply import reply
from interaction.chat import handle_chat
from llm.llm import setup_llm_service

intents = Intents.default()
intents.message_content = True
intents.members = True

bot = Bot(intents=intents)


@bot.event
async def on_ready():
    await setup_llm_service(bot)
    print(f"Logged in as {bot.user}")


@bot.event
async def on_message(message: Message):
    await fun(bot, message)
    await reply(bot, message)
    await handle_chat(bot, message)


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
