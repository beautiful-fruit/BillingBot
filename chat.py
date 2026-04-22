from discord import Bot, Message, TextChannel
from openai_service import get_openai_service

from re import findall


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
        response = await openai_service.process_message(
            bot=bot,
            user=message.author,
            message=message,
        )

        members = message.channel.members \
            if isinstance(message.channel, TextChannel) else []

        members_id_map = {
            str(member.id): member
            for member in members
        }

        mentions = findall(r"<@!?(\d+)>", response)
        if len(mentions) >= 5:
            for mention in mentions:
                response = response.replace(
                    f"<@{mention}>",
                    members_id_map[mention].display_name
                    if mention in members_id_map
                    else f"{mention}(id:{mention})"
                )
                response = response.replace(
                    f"<@!{mention}>",
                    members_id_map[mention].display_name
                    if mention in members_id_map
                    else f"{mention}(id:{mention})"
                )

        await message.reply(response, mention_author=False)

    except Exception as e:
        error_msg = f"抱歉，處理訊息時發生錯誤: {str(e)}"
        await message.reply(error_msg)
