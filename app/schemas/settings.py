"""
Pydantic schemas for Settings endpoints.

Follows Layer 3 rules:
- ALWAYS use Pydantic models for request/response
- Never expose internal IDs or fields that should be hidden
- Use dedicated response schemas that exclude sensitive fields
"""
from __future__ import annotations
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional


class GeneralSettingsBase(BaseModel):
    """Base schema for general settings with all fields."""
    name: str = Field(..., description="Public name of the organization/tenant", min_length=1)
    logo_url: Optional[str] = Field(default=None, description="URL to the logo (stored in Spaces or CDN)")
    website_url: Optional[str] = Field(default=None, description="Main website URL of the company")
    short_description: Optional[str] = Field(default=None, description="Short description of the organization")
    mission: Optional[str] = Field(default=None, description="Organization mission statement")
    vision: Optional[str] = Field(default=None, description="Organization vision statement")
    purpose: Optional[str] = Field(default=None, description="Overall purpose of the company/Annie in this tenant")
    customer_problems: Optional[str] = Field(default=None, description="Problems customers typically face")


class GeneralSettingsRead(GeneralSettingsBase):
    """Response schema for reading general settings."""
    tenant_id: str = Field(..., description="Tenant identifier")
    created_at: str = Field(..., description="Creation timestamp (ISO format)")
    updated_at: str = Field(..., description="Last update timestamp (ISO format)")

    class Config:
        from_attributes = True


class GeneralSettingsUpdate(BaseModel):
    """Request schema for updating general settings (all fields optional)."""
    name: Optional[str] = Field(default=None, description="Public name of the organization/tenant", min_length=1)
    logo_url: Optional[str] = Field(default=None, description="URL to the logo (stored in Spaces or CDN)")
    website_url: Optional[str] = Field(default=None, description="Main website URL of the company")
    short_description: Optional[str] = Field(default=None, description="Short description of the organization")
    mission: Optional[str] = Field(default=None, description="Organization mission statement")
    vision: Optional[str] = Field(default=None, description="Organization vision statement")
    purpose: Optional[str] = Field(default=None, description="Overall purpose of the company/Annie in this tenant")
    customer_problems: Optional[str] = Field(default=None, description="Problems customers typically face")


class AutofillRequest(BaseModel):
    """Request schema for autofill from URL."""
    website_url: str = Field(..., description="Public website URL to extract information from")


class AutofillResponse(BaseModel):
    """Response schema for autofill suggestions."""
    name: Optional[str] = Field(default=None, description="Extracted organization name")
    short_description: Optional[str] = Field(default=None, description="Extracted short description")
    mission: Optional[str] = Field(default=None, description="Extracted mission statement")
    vision: Optional[str] = Field(default=None, description="Extracted vision statement")
    purpose: Optional[str] = Field(default=None, description="Extracted purpose")
    customer_problems: Optional[str] = Field(default=None, description="Extracted customer problems")

