# API Conventions

This document outlines the conventions and best practices for the Hermes API.

## Field Naming: camelCase for JSON, snake_case for Python

### Problem

JavaScript/TypeScript frontends expect `camelCase` field names, while Python code uses `snake_case` by convention. This mismatch can cause bugs and confusion.

### Solution: CamelCaseModel

We use Pydantic v2's built-in `alias_generator` to automatically convert between naming conventions:

```python
from app.models.base import CamelCaseModel

class UserResponse(CamelCaseModel):
    """User response model."""

    user_id: int        # Python: snake_case
    is_active: bool     # Python: snake_case
    created_at: str     # Python: snake_case
```

**API Response (automatic conversion):**
```json
{
  "userId": 123,
  "isActive": true,
  "createdAt": "2025-11-09T10:00:00Z"
}
```

### Base Model Implementation

Located in `app/models/base.py`:

```python
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

class CamelCaseModel(BaseModel):
    """
    Base model that automatically converts snake_case fields to camelCase in JSON.

    Configuration:
        - alias_generator: Auto converts field names to camelCase
        - populate_by_name: Accepts both snake_case and camelCase on input
        - from_attributes: Allows creation from ORM models (SQLAlchemy)
    """
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )
```

### Usage Guidelines

#### ✅ DO: Use CamelCaseModel for All API Response Models

```python
# Response models (sent to frontend)
class UserResponse(CamelCaseModel):
    user_id: int
    is_admin: bool

# Input models (received from frontend)
class UserCreate(CamelCaseModel):
    username: str
    email: str
```

#### ✅ DO: Use snake_case in Python Code

```python
# Python code uses snake_case
user = User(
    user_id=123,
    is_active=True,
    created_at="2025-11-09"
)
```

#### ❌ DON'T: Manually Add Field Aliases

```python
# ❌ WRONG - Don't do this!
class UserResponse(BaseModel):
    user_id: int = Field(..., alias="userId", serialization_alias="userId")
    is_active: bool = Field(..., alias="isActive", serialization_alias="isActive")

# ✅ CORRECT - Use CamelCaseModel instead
class UserResponse(CamelCaseModel):
    user_id: int
    is_active: bool
```

#### ✅ DO: Inherit from CamelCaseModel for Consistency

All models in these locations should use `CamelCaseModel`:
- `app/api/v1/endpoints/*.py` - Endpoint-specific models
- `app/models/pydantic/*.py` - Shared models

### Benefits

1. **Automatic Conversion**: No manual aliases needed
2. **Type Safety**: Python types stay clean and simple
3. **Flexibility**: Accepts both formats on input (`populate_by_name=True`)
4. **Consistency**: One pattern across the entire API
5. **Maintainability**: Change once in base model, applies everywhere

### OpenAPI Schema

FastAPI automatically generates correct OpenAPI schemas with camelCase:

```yaml
UserResponse:
  properties:
    userId:
      type: integer
    isActive:
      type: boolean
    createdAt:
      type: string
```

### Testing

Tests should expect camelCase in API responses:

```python
def test_user_response():
    response = client.get("/api/v1/users/1")
    data = response.json()

    # ✅ CORRECT - Check for camelCase
    assert "userId" in data
    assert "isActive" in data

    # ❌ WRONG - Don't check for snake_case
    assert "user_id" in data  # This will fail!
```

### Common Patterns

**Response Model:**
```python
class DownloadResponse(CamelCaseModel):
    download_id: str
    file_name: str
    is_complete: bool
    created_at: str
```

**Input Model:**
```python
class DownloadCreate(CamelCaseModel):
    url: str
    download_subtitles: bool = False
    output_directory: str | None = None
```

**List Response:**
```python
class DownloadListItem(CamelCaseModel):
    download_id: str
    status: str
    progress_percent: int
```

### Exceptions

**Simple fields without underscores don't need special handling:**
```python
class SimpleModel(CamelCaseModel):
    id: str          # No conversion needed
    name: str        # No conversion needed
    status: str      # No conversion needed
```

### Migration from Manual Aliases

If you find models with manual `Field(alias=...)`, refactor them:

**Before:**
```python
class OldModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    is_active: bool = Field(..., alias="isActive", serialization_alias="isActive")
    created_at: str = Field(..., alias="createdAt", serialization_alias="createdAt")
```

**After:**
```python
class NewModel(CamelCaseModel):
    is_active: bool
    created_at: str
```

### References

- [Pydantic v2 Alias Documentation](https://docs.pydantic.dev/latest/concepts/alias/)
- [Pydantic Alias Generators](https://docs.pydantic.dev/latest/api/alias_generators/)
- Base Model Implementation: `app/models/base.py`

### History

- **2025-11-09**: Implemented CamelCaseModel with Pydantic v2 `alias_generator`
- **Reason**: Standardize API responses to use camelCase for JavaScript/TypeScript frontends
- **Impact**: Reduced boilerplate by ~60%, improved maintainability
