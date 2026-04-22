from discord import Bot, Message
from typing import Optional
from openai_service import get_openai_service
from db import get_db
from repository.chat_repository import ChatRepository


async def handle_chat(bot: Bot, message: Message) -> None:
    """
    處理聊天訊息，當機器人被 mention 時回應
    返回 True 表示已處理，False 表示未處理
    """
    user = message.author
    bot_user = bot.user

    if bot_user is None or bot_user == user or user.bot:
        return

    if bot_user not in message.mentions:
        return

    # 移除 mention 部分，取得純文字內容
    content = message.content
    for mention_user in message.mentions:
        content = content.replace(
            mention_user.mention,
            f"{mention_user.display_name}(id:{mention_user.id})"
        )

    content = content.strip()

    # 清除對話歷史命令
    # clear_commands = ["!clear", "!clear_chat", "!清除", "!清空"]
    # if content.lower() in clear_commands:
    #     try:
    #         async with get_db() as conn:
    #             await ChatRepository.clear_channel_history(conn, message.channel.id)
    #         await message.reply("已清除此頻道的對話歷史。")
    #     except Exception as e:
    #         await message.reply(f"清除歷史時發生錯誤: {str(e)}")
    #     return True

    try:
        openai_service = get_openai_service()
    except ValueError as e:
        await message.reply(f"聊天功能無法使用: {str(e)}")
        return
    except Exception as e:
        await message.reply(f"初始化聊天服務時發生錯誤: {str(e)}")
        return

    try:
        thinking_msg = await message.reply("思考中...")

        response = await openai_service.process_message(
            channel_id=message.channel.id,
            user_message=content,
            user_id=message.author.id,
            username=message.author.name
        )

        await thinking_msg.edit(content=response)

    except Exception as e:
        error_msg = f"抱歉，處理訊息時發生錯誤: {str(e)}"
        await message.reply(error_msg)
