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

    if "超好笑" in message.content:
        await message.reply("不好笑")
    elif "好" in message.content:
        await message.reply("不好")

    target_id = 712676831911739482
    if any(u.id == target_id for u in message.mentions):
        channel = message.channel
        target_member = next(u for u in message.mentions if u.id == target_id)
        if hasattr(target_member, "roles"):
            mentions = [
                role.mention 
                for role in target_member.roles[1:] 
                if len(role.members) == 1
            ]
            mentions.insert(0, target_member.mention)
            main_mention = target_member.mention
            content = message.content.rsplit(main_mention, 1)[-1]
            if main_mention in content:
                content = content.replace(main_mention, "")
            content = content.strip()

            if mentions:
                results = "\n".join([
                    f"{mention} {content}" for mention in mentions
                ])
                await channel.send(results)

        # for mention in mentions:
        #     await channel.send(f"{mention} {content}")
