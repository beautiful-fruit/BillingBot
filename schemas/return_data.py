from pydantic import BaseModel, Field, model_validator

from typing import Optional

from snowflake import SnowflakeID, SnowflakeGenerator

generator = SnowflakeGenerator()


class Return(BaseModel):
    uid: SnowflakeID = Field(default_factory=generator.next_id)
    from_uid: int
    to_uid: int
    amount: int
    pending: bool = True

    @model_validator(mode="after")
    def validate_positive_amount(self) -> "Return":
        if self.from_uid == self.to_uid:
            raise ValueError("'from_uid' and 'to_uid' cannot be the same.")
        if self.amount <= 0:
            self.amount = -self.amount
            self.from_uid, self.to_uid = self.to_uid, self.from_uid
        return self
    
    @property
    def insert_query(self) -> tuple[str, tuple]:
        return """
            INSERT INTO return_history (uid, from_uid, to_uid, amount, pending)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, (self.uid.value, self.from_uid, self.to_uid, self.amount, self.pending)
