from discord import Bot, Message, TextChannel
from llm.llm import get_llm_service

from re import findall


async def handle_chat(bot: Bot, message: Message) -> None:
    user = message.author
    bot_user = bot.user

    if bot_user is None or bot_user == user or user.bot:
        return

    if bot_user not in message.mentions:
        return

    content = message.content
    for mention_user in message.mentions:
        content = content.replace(
            mention_user.mention,
            f"{mention_user.display_name}(id:{mention_user.id})"
        )

    content = content.strip()

    try:
        llm_service = get_llm_service()
    except ValueError as e:
        await message.reply(f"聊天功能無法使用: {str(e)}")
        return
    except Exception as e:
        await message.reply(f"初始化聊天服務時發生錯誤: {str(e)}")
        return

    try:
        async with message.channel.typing():
            response = await llm_service.process_message(
                message=message,
            )
        await message.reply(response, mention_author=False)
    except Exception as e:
        error_msg = f"抱歉，處理訊息時發生錯誤: {str(e)}"
        await message.reply(error_msg)
