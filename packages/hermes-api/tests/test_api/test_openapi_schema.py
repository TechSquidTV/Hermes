"""
Tests for OpenAPI schema validation.

Ensures that all API models follow the camelCase convention for JSON fields.
"""

import pytest


class TestOpenAPISchema:
    """Test OpenAPI schema conventions."""

    def _find_snake_case_fields(self, node, path="schema"):
        """Find snake_case property names anywhere in an OpenAPI schema node."""
        errors = []

        if isinstance(node, dict):
            properties = node.get("properties", {})
            if isinstance(properties, dict):
                for field_name, field_schema in properties.items():
                    if "_" in field_name and not field_name.startswith("__"):
                        errors.append(f"{path}.{field_name}")
                    errors.extend(
                        self._find_snake_case_fields(
                            field_schema, f"{path}.{field_name}"
                        )
                    )

            for key in ("items", "additionalProperties", "allOf", "anyOf", "oneOf"):
                value = node.get(key)
                if isinstance(value, list):
                    for index, item in enumerate(value):
                        errors.extend(
                            self._find_snake_case_fields(item, f"{path}.{key}[{index}]")
                        )
                elif value is not None:
                    errors.extend(self._find_snake_case_fields(value, f"{path}.{key}"))

        return errors

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
            errors.extend(self._find_snake_case_fields(schema_def, schema_name))

        # Also check inline schemas on path responses and request bodies. Plain
        # dict response models otherwise bypass component-level validation.
        for route_path, path_def in schema.get("paths", {}).items():
            for method, operation in path_def.items():
                if method not in {
                    "get",
                    "put",
                    "post",
                    "delete",
                    "options",
                    "head",
                    "patch",
                    "trace",
                }:
                    continue

                for status_code, response in operation.get("responses", {}).items():
                    for media_type, media in response.get("content", {}).items():
                        schema_def = media.get("schema")
                        if schema_def:
                            errors.extend(
                                self._find_snake_case_fields(
                                    schema_def,
                                    f"{method.upper()} {route_path} {status_code} {media_type}",
                                )
                            )

                request_body = operation.get("requestBody", {})
                for media_type, media in request_body.get("content", {}).items():
                    schema_def = media.get("schema")
                    if schema_def:
                        errors.extend(
                            self._find_snake_case_fields(
                                schema_def,
                                f"{method.upper()} {route_path} request {media_type}",
                            )
                        )

        if errors:
            error_list = "\n  - ".join(errors[:10])
            more_msg = (
                f"\n  ... and {len(errors) - 10} more" if len(errors) > 10 else ""
            )
            pytest.fail(
                f"Found {len(errors)} snake_case fields in OpenAPI schema:\n  - {error_list}{more_msg}\n\n"
                f"All API fields should use camelCase. Use CamelCaseModel base class."
            )

    @pytest.mark.asyncio
    async def test_standard_error_responses_use_error_response_schema(self):
        """Common HTTP errors should document the runtime ErrorResponse wrapper."""
        from app.main import STANDARD_ERROR_RESPONSES, app

        schema = app.openapi()
        schemas = schema.get("components", {}).get("schemas", {})
        assert "Error" in schemas
        assert "ErrorResponse" in schemas

        error_ref = {"$ref": "#/components/schemas/Error"}
        error_response_ref = {"$ref": "#/components/schemas/ErrorResponse"}

        assert schemas["ErrorResponse"]["properties"]["error"] == error_ref
        assert "additionalProperties" not in schemas["Error"]["properties"]["details"]

        auth_me_responses = schema["paths"]["/api/v1/auth/me"]["get"]["responses"]
        for status_code in STANDARD_ERROR_RESPONSES:
            response = auth_me_responses[str(status_code)]
            assert (
                response["content"]["application/json"]["schema"] == error_response_ref
            )

        info_responses = schema["paths"]["/api/v1/info/"]["get"]["responses"]
        assert info_responses["422"]["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/HTTPValidationError"
        }
