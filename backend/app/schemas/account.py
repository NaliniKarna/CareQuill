from pydantic import BaseModel, Field


class AccountDeleteRequest(BaseModel):
    """Deleting an account is irreversible, so it needs the password again
    (a stolen access token alone must not be enough) and an explicit
    confirmation phrase."""

    password: str = Field(min_length=1, max_length=128)
    confirmation: str = Field(description='Must be exactly "DELETE".')
