from pydantic import BaseModel, ConfigDict


class TelegramIDModel(BaseModel):
    telegram_id: int

    model_config = ConfigDict(from_attributes=True)


class UserModel(TelegramIDModel):
    username: str | None
    first_name: str | None
    last_name: str | None
    best_score: int = 0


class SetBestScoreRequest(BaseModel):
    score: int


class SetBestScoreResponse(BaseModel):
    status: str
    best_score: int
