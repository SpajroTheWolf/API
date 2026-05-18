from pydantic import BaseModel


class RegisterSchema(BaseModel):
    username: str
    password: str


class LoginSchema(BaseModel):
    username: str
    password: str
    hardware_id: str


class RedeemSchema(BaseModel):
    username: str
    key: str


class CreateKeySchema(BaseModel):
    admin_token: str
    duration_days: int


class ResetHWIDSchema(BaseModel):
    username: str
    admin_token: str