from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.core.password_policy import WeakPasswordError, validate_password_strength
from app.schemas.user import UserRead


def _check_strength(value: str, email: str | None = None) -> str:
    try:
        return validate_password_strength(value, email=email)
    except WeakPasswordError as exc:
        raise ValueError(str(exc)) from exc


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(max_length=128)
    # Explicit consent to the Terms and Privacy Policy. Required: the account
    # holds sensitive health data and the patient must agree knowingly.
    accepted_terms: bool

    @field_validator("accepted_terms")
    @classmethod
    def _must_accept(cls, value: bool) -> bool:
        if not value:
            raise ValueError("You must accept the Terms and Privacy Policy to create an account.")
        return value

    @model_validator(mode="after")
    def _strong_password(self) -> "RegisterRequest":
        _check_strength(self.password, str(self.email))
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AuthResponse(TokenPair):
    user: UserRead


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(max_length=128)

    @field_validator("new_password")
    @classmethod
    def _strong(cls, value: str) -> str:
        return _check_strength(value)


class VerifyEmailRequest(BaseModel):
    token: str


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(max_length=128)

    @field_validator("new_password")
    @classmethod
    def _strong(cls, value: str) -> str:
        return _check_strength(value)
