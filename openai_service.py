import os
from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionSystemMessageParam,
    ChatCompletionUserMessageParam,
    ChatCompletionAssistantMessageParam,
)
from openai.types.responses.response_input_item_param import Message

from typing import Optional, TypeAlias, Union

from db import get_db
from repository.chat_repository import ChatRepository
from schemas.chat_message import ChatMessage

AIChatMessage: TypeAlias = Union[ChatCompletionSystemMessageParam,
                                 ChatCompletionUserMessageParam, ChatCompletionAssistantMessageParam]


class OpenAIService:
    client: AsyncOpenAI
    model: str
    system_prompt: str
    max_history_messages: int = 1000
    max_tokens: int = 10_000

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        base_url = os.getenv("OPENAI_API_BASE_URL")
        model = os.getenv("OPENAI_MODEL")

        if not api_key or not base_url or not model:
            raise ValueError(
                "OPENAI_API_KEY, OPENAI_API_BASE_URL, and OPENAI_MODEL must be set in environment variables.")

        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)

        self.model = model
        with open("system_prompt.md", "r", encoding="utf-8") as f:
            self.system_prompt = f.read()

    async def process_message(
        self,
        channel_id: int,
        user_message: str,
        user_id: int,
        username: str
    ) -> str:
        async with get_db() as conn:
            await ChatRepository.insert(
                conn=conn,
                channel_id=channel_id,
                role="user",
                content=user_message,
                message_id=user_id
            )

            history = await ChatRepository.get_channel_history(
                conn=conn,
                channel_id=channel_id,
                limit=self.max_history_messages * 2
            )

            messages = await self._build_messages(history, user_message, username)

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=0.7
            )

            assistant_response = response.choices[0].message.content
            if assistant_response is None:
                assistant_response = "抱歉，我無法產生回應。"

            await ChatRepository.insert(
                conn=conn,
                channel_id=channel_id,
                role="assistant",
                content=assistant_response,
                user_id=None,
                username=None
            )

            total_tokens = response.usage.total_tokens if response.usage else 0
            if total_tokens > self.max_tokens:
                # 清理舊訊息以保持資料庫整潔（刪除前15%的訊息）
                await ChatRepository.delete_old_messages(
                    conn=conn,
                    channel_id=channel_id,
                    percentage=0.15
                )

            return assistant_response

    async def _build_messages(
        self,
        history: list[ChatMessage],
        current_message: str,
        current_username: Optional[str] = None
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
                    "content": msg.content,
                    "name": msg.username or ""
                })
            elif msg.role == "assistant":
                messages.append({
                    "role": "assistant",
                    "content": msg.content
                })

        messages.append({
            "role": "user",
            "content": current_message,
            "name": current_username or ""
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
