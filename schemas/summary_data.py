from pydantic import BaseModel, model_validator


class Summary(BaseModel):
    user1: int
    user2: int
    amount: int

    @model_validator(mode="after")
    def validate_user_order(self) -> "Summary":
        if self.user1 > self.user2:
            self.user1, self.user2 = self.user2, self.user1
        return self
