from pydantic import BaseModel


class User(BaseModel):
    uid: int
