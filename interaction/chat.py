from discord import Bot, Message, TextChannel, Thread

from llm.llm import get_llm_service
from utils.send_like_human import send_like_human


async def handle_chat(bot: Bot, message: Message) -> None:
    user = message.author
    bot_user = bot.user

    if bot_user is None or bot_user == user or user.bot:
        return None

    if bot_user not in message.mentions:
        return None

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
        return None
    except Exception as e:
        await message.reply(f"初始化聊天服務時發生錯誤: {str(e)}")
        return None

    try:
        async with message.channel.typing():
            response = await llm_service.process_message(
                message=message,
            )

        if not isinstance(message.channel, (TextChannel, Thread)):
            await message.reply("無法回覆訊息: 頻道類型不受支持")
            return None

        await send_like_human(message.channel, response)
    except Exception as e:
        error_msg = f"抱歉，處理訊息時發生錯誤: {str(e)}"
        await message.reply(error_msg)
