from pydantic import BaseModel, Field


class UserRegister(BaseModel):
    email: str = Field(min_length=3)
    password: str = Field(min_length=6)


class UserLogin(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
