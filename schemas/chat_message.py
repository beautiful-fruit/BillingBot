from pydantic import BaseModel, Field
from pydantic_snowflake import SnowflakeId, SnowflakeGenerator
from typing import Optional, Literal, TypeAlias


generator = SnowflakeGenerator()

ChatRoleName: TypeAlias = Literal["user", "assistant", "system"]


class ChatMessage(BaseModel):
    id: SnowflakeId = Field(default_factory=generator.next)
    channel_id: int
    user_id: Optional[int] = None
    username: Optional[str] = None
    role: ChatRoleName
    content: str
    message_id: Optional[int] = None

    @property
    def insert_query(self) -> tuple[str, tuple]:
        return """
            INSERT INTO chat_messages (id, channel_id, user_id, username, role, content, message_id)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, (self.id.value, self.channel_id, self.user_id, self.username, self.role, self.content, self.message_id)
