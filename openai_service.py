from discord import Message, Member, User, TextChannel, Bot
from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionMessageFunctionToolCall,
    ChatCompletionToolMessageParam,
    ChatCompletionToolUnionParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
    ChatCompletionAssistantMessageParam,
)
from pydantic_snowflake import SnowflakeId

from asyncio import get_event_loop
from json import loads, dumps
from os import getenv
from typing import Optional, TypeAlias, Union

from db import get_db
from repository.chat_repository import ChatRepository
from schemas.chat_message import ChatMessage

AIChatMessage: TypeAlias = Union[
    ChatCompletionToolMessageParam,
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
    ChatCompletionAssistantMessageParam,
]

# 定義可用工具
TOOLS: list[ChatCompletionToolUnionParam] = [
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
        messages = await self._build_messages(history=history)

        max_tool_iterations = 3
        iteration = 0
        final_response = None

        response = None
        while iteration < max_tool_iterations:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=TOOLS,
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
                if isinstance(tool_call, ChatCompletionMessageFunctionToolCall):
                    function_name = tool_call.function.name
                    function_args = loads(
                        tool_call.function.arguments)

                    if function_name == "get_channel_members":
                        # 獲取頻道成員
                        members = channel.members
                        print(
                            f"Channel members: {[member.display_name for member in members]}")
                        member_list = []
                        for member in members:
                            member_list.append({
                                "id": str(member.id),
                                "name": member.display_name,
                            })
                        result = dumps(
                            member_list, ensure_ascii=False)
                    elif function_name == "get_user_by_id":
                        user_id = int(function_args["user_id"])
                        # 嘗試從頻道獲取成員，否則從公會獲取
                        try:
                            member = channel.guild.get_member(user_id)
                        except:
                            member = None

                        if member:
                            result = dumps({
                                "id": str(member.id),
                                "name": member.display_name,
                                "joined_at": str(member.joined_at) if member.joined_at else None,
                                "roles": [{"id": str(role.id), "name": role.name} for role in member.roles]
                            }, ensure_ascii=False)
                        else:
                            # 如果找不到成員，嘗試獲取使用者（可能不在公會中）
                            res_user = bot.get_user(user_id)
                            if res_user:
                                result = dumps({
                                    "id": str(res_user.id),
                                    "name": res_user.name,
                                    "discriminator": res_user.discriminator,
                                }, ensure_ascii=False)
                            else:
                                result = dumps({"error": "找不到該使用者"})

                    else:
                        result = dumps(
                            {"error": f"未知工具: {function_name}"})

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

        async with get_db() as conn:
            await ChatRepository.insert(
                conn=conn,
                channel_id=channel.id,
                role="assistant",
                content=final_response,
            )

        total_tokens = response.usage.total_tokens if response and response.usage else 0
        print(f"Total tokens used: {total_tokens}")
        if total_tokens > self.max_tokens:
            async def __task():
                messages.append({
                    "role": "assistant",
                    "content": final_response
                })
                messages.append({
                    "role": "system",
                    "content": "".join([
                        "The conversation has exceeded the maximum token limit. ",
                        "Please summarize the conversation and remove irrelevant details to reduce the token count while keeping the main context.",
                        "You should keep the important information and the overall style of the conversation, but you can remove some of the less important details, such as greetings, farewells, and some of the chit-chat. ",
                        "The goal is to reduce the total token count of the conversation history while retaining the main context and style, so that the conversation can continue without hitting the token limit.",
                        "Please provide a concise summary of the conversation so far, and make sure to keep the important information and the overall style of the conversation. ",
                        "The summary should be in the same format as the original messages, but you can remove some of the less important details to reduce the token count. ",
                        "Remember to keep the main context and style of the conversation, while reducing the total token count to allow the conversation to continue."
                    ])
                })

                summary_response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7
                )

                async with get_db() as conn:
                    if summary_response.choices and len(summary_response.choices) > 0:
                        choice = summary_response.choices[0]
                        message_response = choice.message
                        await ChatRepository.insert(
                            conn=conn,
                            channel_id=channel.id,
                            role="system",
                            content="[Conversation Summary]: " +
                            (message_response.content or "")
                        )
                    # 清理舊訊息以保持資料庫整潔（刪除前15%的訊息）
                    await ChatRepository.delete_old_messages(
                        conn=conn,
                        channel_id=channel.id,
                        percentage=0.15
                    )
            loop = get_event_loop()
            loop.create_task(__task())

        return final_response

    async def _build_messages(
        self,
        history: list[ChatMessage]
    ) -> list[AIChatMessage]:
        messages: list[AIChatMessage] = [
            {"role": "system", "content": self.system_prompt}
        ]

        # 添加歷史訊息（排除系統訊息）
        for msg in history:
            if msg.role == "user":
                messages.append({
                    "role": "user",
                    "content": f"[{msg.id.datetime.isoformat()} {msg.username}<@{msg.user_id}>]: {msg.content}",
                })
            elif msg.role == "assistant":
                messages.append({
                    "role": "assistant",
                    "content": msg.content
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
