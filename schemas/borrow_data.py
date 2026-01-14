from pydantic import BaseModel, Field, model_validator

from typing import Optional

from snowflake import SnowflakeID, SnowflakeGenerator

generator = SnowflakeGenerator()


class Borrow(BaseModel):
    uid: SnowflakeID = Field(default_factory=generator.next_id)
    from_uid: int
    to_uid: int
    amount: Optional[int] = None
    other: Optional[str] = None
    url: str
    pending: bool = True

    @model_validator(mode="before")
    def check_amount_or_other(cls, data: dict) -> dict:
        if data.get("amount") is None and data.get("other") is None:
            raise ValueError("Either 'amount' or 'other' must be provided.")
        return data

    @model_validator(mode="after")
    def validate_positive_amount(self) -> "Borrow":
        if self.from_uid == self.to_uid:
            raise ValueError("'from_uid' and 'to_uid' cannot be the same.")
        if self.amount is not None and self.amount <= 0:
            self.amount = -self.amount
            self.from_uid, self.to_uid = self.to_uid, self.from_uid
        return self

    @property
    def insert_query(self) -> tuple[str, tuple]:
        return """
            INSERT INTO borrow_history (uid, from_uid, to_uid, amount, other, url, pending)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
        """, (self.uid.value, self.from_uid, self.to_uid, self.amount, self.other, self.url, self.pending)
