"""
Base Pydantic models for API schemas.

This module provides base models that automatically handle snake_case to
camelCase conversion for API responses, following industry best practices.
"""

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CamelCaseModel(BaseModel):
    """
    Base model that automatically converts snake_case fields to camelCase in JSON.

    This ensures consistent API responses where Python code uses snake_case
    internally but the API returns camelCase to match JavaScript conventions.

    Example:
        class UserResponse(CamelCaseModel):
            user_id: int        # → "userId" in JSON
            is_active: bool     # → "isActive" in JSON
            created_at: str     # → "createdAt" in JSON

    Configuration:
        - alias_generator: Automatically converts field names to camelCase
        - populate_by_name: Accepts both snake_case and camelCase on input
        - from_attributes: Allows creation from ORM models (SQLAlchemy)
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
