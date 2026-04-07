from discord import Bot, Embed, EmbedAuthor, Message

from asyncio import sleep as asleep
from datetime import datetime
from os import getenv

SPEC_USER_ID = int(getenv("SPEC_USER_ID", "0"))
SPEC_SHELL_PATH = getenv("SPEC_SHELL_PATH", "")


async def fun(bot: Bot, message: Message):
    user = message.author
    bot_user = bot.user

    if bot_user is None or bot_user == user or user.bot:
        return

    if "毀滅" in message.content:
        if user.id == SPEC_USER_ID:
            embed = Embed(
                color=0xFF8800,
                title="毀滅!!!",
                description=f"毀滅",
                timestamp=datetime.now(),
                author=EmbedAuthor(
                    name=bot_user.display_name,
                    icon_url=bot_user.display_avatar.url,
                ),
                thumbnail=user.display_avatar.url,
            )

            await message.reply(
                embed=embed
            )
            await asleep(1)
            await message.channel.send("3...")
            await asleep(1)
            await message.channel.send("2...")
            await asleep(1)
            await message.channel.send("1...")
            await asleep(1)
            await message.channel.send("毀滅!!")

            from subprocess import run
            run([SPEC_SHELL_PATH])
        else:
            await message.reply("毀滅")

    if "今" in message.content:
        await message.reply("今日敢於獨行怪癖之人寥若晨星，正是這個時代大為可懼的標誌。")

    if "特別怪" in message.content:
        await message.reply("特別怪")
    elif "超怪" in message.content:
        await message.reply("超怪")
    elif "好怪" in message.content:
        await message.reply("好怪")
    elif "怪" in message.content:
        await message.reply("怪")

    if "❓" in message.content or ":question:" in message.content:
        await message.reply("❓")

    if 712676831911739482 in list(map(lambda u: u.id, message.mentions)):
        channel = message.channel
        main_mention = "<@712676831911739482>"
        mentions = [
            "<@712676831911739482>",
            "<@&1474010223592341514>",
            "<@&1474010833917968475>",
            "<@&1456944613884563488>",
            "<@&1483534240674086992>",
            "<@&1371190001987092490>",
            "<@&1370723863935062079>",
            "<@&1479411931398799360>",
            "<@&1286240209268244490>",
            "<@&1474010447001948200>",
            "<@&1474026056242696273>"
        ]
        content = message.content.rsplit(main_mention, 1)[-1]
        if main_mention in content:
            content = content.replace(main_mention, "")
        content = content.strip()

        for mention in mentions:
            await channel.send(f"{mention} {content}")
