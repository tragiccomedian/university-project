"""Base Pydantic schemas with shared configuration."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AppBaseModel(BaseModel):
    """All schemas inherit from this to share serialization config."""

    model_config = ConfigDict(
        from_attributes=True,  # allows model_validate(orm_instance)
        populate_by_name=True,  # accept both alias and field name
        use_enum_values=True,
    )


class TimestampSchema(AppBaseModel):
    created_at: datetime
    updated_at: datetime


class PaginatedResponse(AppBaseModel):
    """Generic paginated list envelope."""

    total: int
    limit: int
    offset: int
    has_next: bool
