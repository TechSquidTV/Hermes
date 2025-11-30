"""
Tests for OpenAPI schema validation.

Ensures that all API models follow the camelCase convention for JSON fields.
"""

import pytest


class TestOpenAPISchema:
    """Test OpenAPI schema conventions."""

    @pytest.mark.asyncio
    async def test_all_fields_use_camelcase(self):
        """Test that all OpenAPI schema fields use camelCase (not snake_case)."""
        from app.main import app

        schema = app.openapi()
        errors = []

        # Check all schemas in components
        for schema_name, schema_def in (
            schema.get("components", {}).get("schemas", {}).items()
        ):
            properties = schema_def.get("properties", {})
            for field_name in properties.keys():
                # Check for snake_case (has underscore)
                if "_" in field_name and not field_name.startswith("__"):
                    errors.append(f"{schema_name}.{field_name}")

        if errors:
            error_list = "\n  - ".join(errors[:10])
            more_msg = (
                f"\n  ... and {len(errors) - 10} more" if len(errors) > 10 else ""
            )
            pytest.fail(
                f"Found {len(errors)} snake_case fields in OpenAPI schema:\n  - {error_list}{more_msg}\n\n"
                f"All API fields should use camelCase. Use CamelCaseModel base class."
            )
