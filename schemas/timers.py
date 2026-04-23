from pydantic import BaseModel, Field
from pydantic_snowflake import SnowflakeId, SnowflakeGenerator

from datetime import datetime

generator = SnowflakeGenerator()


class TimerData(BaseModel):
    id: SnowflakeId = Field(default_factory=generator.next)
    channel_id: int
    user_id: int
    trigger_time: datetime
    message: str
    original_message: str

    @property
    def insert_query(self) -> tuple[str, tuple]:
        return """
            INSERT INTO timers (id, channel_id, user_id, trigger_time, message)
            VALUES ($1, $2, $3, $4, $5)
        """, (self.id.value, self.channel_id, self.user_id, self.trigger_time, self.message)
