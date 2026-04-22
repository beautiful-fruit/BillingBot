from discord import Message, Member, User, TextChannel, Bot
from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
    ChatCompletionAssistantMessageParam,
)

import json
from os import getenv
from typing import Optional, TypeAlias, Union

from db import get_db
from repository.chat_repository import ChatRepository
from schemas.chat_message import ChatMessage

AIChatMessage: TypeAlias = Union[
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
    ChatCompletionAssistantMessageParam
]


class OpenAIService:
    client: AsyncOpenAI
    model: str
    system_prompt: str
    max_history_messages: int = 1000
    max_tokens: int = 10_000

    def __init__(self):
        api_key = getenv("OPENAI_API_KEY")
        base_url = getenv("OPENAI_API_BASE_URL")
        model = getenv("OPENAI_MODEL")

        if not api_key or not base_url or not model:
            raise ValueError(
                "OPENAI_API_KEY, OPENAI_API_BASE_URL, and OPENAI_MODEL must be set in environment variables.")

        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

        self.model = model
        with open("system_prompt.md", "r", encoding="utf-8") as f:
            self.system_prompt = f.read()

    async def process_message(
        self,
        bot: Bot,
        user: Union[Member, User],
        message: Message,
    ) -> str:
        channel = message.channel
        if not isinstance(channel, TextChannel):
            return "抱歉，我只能在文字頻道中回應。"
        
        channel_members = channel.members

        async with get_db() as conn:
            await ChatRepository.insert(
                conn=conn,
                channel_id=channel.id,
                role="user",
                content=message.content,
                user_id=user.id,
                username=user.display_name,
                message_id=message.id
            )

            history = await ChatRepository.get_channel_history(
                conn=conn,
                channel_id=channel.id,
                limit=self.max_history_messages * 2
            )

            messages = await self._build_messages(
                history=history,
                message=message,
                user=user
            )

            # 定義可用工具
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": "get_channel_members",
                        "description": "獲取當前頻道的所有使用者列表",
                        "parameters": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    }
                },
                {
                    "type": "function",
                    "function": {
                        "name": "get_user_by_id",
                        "description": "通過使用者ID獲取使用者資料",
                        "parameters": {
                            "type": "object",
                            "properties": {
                                "user_id": {
                                    "type": "string",
                                    "description": "Discord 使用者 ID"
                                }
                            },
                            "required": ["user_id"]
                        }
                    }
                }
            ]

            max_tool_iterations = 3
            iteration = 0
            final_response = None

            response = None
            while iteration < max_tool_iterations:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=tools,
                    tool_choice="auto",
                    temperature=0.95
                )

                choice = response.choices[0]
                message_response = choice.message
                tool_calls = message_response.tool_calls

                # 如果沒有工具調用，則返回回應
                if not tool_calls:
                    final_response = message_response.content
                    if final_response is None:
                        final_response = "抱歉，我無法產生回應。"
                    break

                # 處理工具調用
                for tool_call in tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    if function_name == "get_channel_members":
                        # 獲取頻道成員
                        members = channel.members
                        member_list = []
                        for member in members:
                            member_list.append({
                                "id": str(member.id),
                                "name": member.display_name,
                                "mention": member.mention
                            })
                        result = json.dumps(member_list, ensure_ascii=False)
                    
                    elif function_name == "get_user_by_id":
                        user_id = int(function_args["user_id"])
                        # 嘗試從頻道獲取成員，否則從公會獲取
                        member = channel.guild.get_member(user_id)
                        if member is None:
                            try:
                                member = channel.guild.get_member(user_id)
                            except:
                                member = None
                        
                        if member:
                            result = json.dumps({
                                "id": str(member.id),
                                "name": member.display_name,
                                "mention": member.mention,
                                "joined_at": str(member.joined_at) if member.joined_at else None,
                                "roles": [{"id": str(role.id), "name": role.name} for role in member.roles]
                            }, ensure_ascii=False)
                        else:
                            # 如果找不到成員，嘗試獲取使用者（可能不在公會中）
                            res_user = bot.get_user(user_id)
                            if res_user:
                                result = json.dumps({
                                    "id": str(res_user.id),
                                    "name": res_user.name,
                                    "discriminator": res_user.discriminator,
                                    "mention": res_user.mention
                                }, ensure_ascii=False)
                            else:
                                result = json.dumps({"error": "找不到該使用者"})
                    
                    else:
                        result = json.dumps({"error": f"未知工具: {function_name}"})

                    # 將工具回應添加到訊息中
                    messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": tool_call.id,
                                "type": "function",
                                "function": {
                                    "name": function_name,
                                    "arguments": tool_call.function.arguments
                                }
                            }
                        ]
                    })
                    messages.append({
                        "role": "tool",
                        "content": result,
                        "tool_call_id": tool_call.id
                    })

                iteration += 1

            if final_response is None:
                final_response = "抱歉，處理工具調用時發生錯誤。"

            await ChatRepository.insert(
                conn=conn,
                channel_id=channel.id,
                role="assistant",
                content=final_response,
            )

            total_tokens = response.usage.total_tokens if response and response.usage else 0
            print(f"Total tokens used: {total_tokens}")
            if total_tokens > self.max_tokens:
                # 清理舊訊息以保持資料庫整潔（刪除前15%的訊息）
                await ChatRepository.delete_old_messages(
                    conn=conn,
                    channel_id=channel.id,
                    percentage=0.15
                )

            return final_response

    async def _build_messages(
        self,
        history: list[ChatMessage],
        message: Message,
        user: Union[Member, User],
    ) -> list[AIChatMessage]:
        messages: list[AIChatMessage] = [
            {"role": "system", "content": self.system_prompt}
        ]

        # 添加歷史訊息（排除系統訊息）
        for msg in history:
            if msg.role == "system":
                continue

            if msg.role == "user":
                messages.append({
                    "role": "user",
                    "content": f"[{msg.username}<@{msg.user_id}>]: {msg.content}",
                })
            elif msg.role == "assistant":
                messages.append({
                    "role": "assistant",
                    "content": msg.content
                })

        messages.append({
            "role": "user",
            "content": f"[{user.display_name}{user.mention}]: {message.content}",
        })

        # 如果訊息過長，進行精簡
        return messages


# 全域實例
openai_service: Optional[OpenAIService] = None


def get_openai_service() -> OpenAIService:
    global openai_service
    if openai_service is None:
        openai_service = OpenAIService()
    return openai_service
