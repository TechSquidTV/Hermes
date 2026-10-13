"""One password policy for account creation and password changes."""

from typing import Annotated

from pydantic import AfterValidator, Field


def validate_password_bytes(value: str) -> str:
    if len(value.encode("utf-8")) > 72:
        raise ValueError("Password must not exceed 72 UTF-8 bytes")
    return value


Password = Annotated[
    str, Field(min_length=8, max_length=72), AfterValidator(validate_password_bytes)
]
