# Backend Settings → General - Complete Implementation

## 📦 All Components

### 1. SQLAlchemy Model

**File:** `app/domain/sqlalchemy_models.py`

```python
class GeneralSettings(Base):
    """
    General settings model for tenant-specific organization information.
    
    One record per tenant (enforced by PRIMARY KEY on tenant_id).
    """
    __tablename__ = "general_settings"
    
    tenant_id = Column(String, ForeignKey("tenants.id", ondelete="CASCADE"), primary_key=True)
    name = Column(String, nullable=False)
    logo_url = Column(String, nullable=True)
    website_url = Column(String, nullable=True)
    short_description = Column(Text, nullable=True)
    mission = Column(Text, nullable=True)
    vision = Column(Text, nullable=True)
    purpose = Column(Text, nullable=True)
    customer_problems = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())
    
    tenant = relationship("Tenant", backref="general_settings")
```

### 2. Database Migration

**File:** `app/db/general_settings_schema.sql`

```sql
BEGIN;

CREATE TABLE IF NOT EXISTS general_settings (
    tenant_id          TEXT PRIMARY KEY REFERENCES tenants(id) ON DELETE CASCADE,
    name               TEXT NOT NULL,
    logo_url           TEXT,
    website_url        TEXT,
    short_description  TEXT,
    mission            TEXT,
    vision             TEXT,
    purpose            TEXT,
    customer_problems  TEXT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_general_settings_tenant ON general_settings(tenant_id);

COMMENT ON TABLE general_settings IS 'General organization settings per tenant';
COMMENT ON COLUMN general_settings.tenant_id IS 'Foreign key to tenants table - one record per tenant';

COMMIT;
```

### 3. Pydantic Schemas

**File:** `app/schemas/settings.py`

```python
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional


class GeneralSettingsBase(BaseModel):
    """Base schema for general settings with all fields."""
    name: str = Field(..., description="Public name of the organization/tenant", min_length=1)
    logo_url: Optional[str] = Field(default=None, description="URL to the logo")
    website_url: Optional[str] = Field(default=None, description="Main website URL")
    short_description: Optional[str] = Field(default=None, description="Short description")
    mission: Optional[str] = Field(default=None, description="Mission statement")
    vision: Optional[str] = Field(default=None, description="Vision statement")
    purpose: Optional[str] = Field(default=None, description="Overall purpose")
    customer_problems: Optional[str] = Field(default=None, description="Customer problems")


class GeneralSettingsRead(GeneralSettingsBase):
    """Response schema for reading general settings."""
    tenant_id: str = Field(..., description="Tenant identifier")
    created_at: str = Field(..., description="Creation timestamp (ISO format)")
    updated_at: str = Field(..., description="Last update timestamp (ISO format)")

    class Config:
        from_attributes = True


class GeneralSettingsUpdate(BaseModel):
    """Request schema for updating general settings (all fields optional)."""
    name: Optional[str] = Field(default=None, description="Public name", min_length=1)
    logo_url: Optional[str] = Field(default=None, description="URL to the logo")
    website_url: Optional[str] = Field(default=None, description="Main website URL")
    short_description: Optional[str] = Field(default=None, description="Short description")
    mission: Optional[str] = Field(default=None, description="Mission statement")
    vision: Optional[str] = Field(default=None, description="Vision statement")
    purpose: Optional[str] = Field(default=None, description="Overall purpose")
    customer_problems: Optional[str] = Field(default=None, description="Customer problems")


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
```

### 4. Service Layer

**File:** `app/services/settings_service.py`

```python
from __future__ import annotations
from repositories.general_settings_repo import get_general_settings, upsert_general_settings
from schemas.settings import GeneralSettingsUpdate, GeneralSettingsRead


def get_settings(tenant_id: str) -> GeneralSettingsRead:
    """
    Get general settings for a tenant.
    Returns default values if no settings exist yet.
    """
    data = get_general_settings(tenant_id)
    
    if not data:
        # Return defaults (lazy creation on first update)
        return GeneralSettingsRead(
            tenant_id=tenant_id,
            name="",
            logo_url=None,
            website_url=None,
            short_description=None,
            mission=None,
            vision=None,
            purpose=None,
            customer_problems=None,
            created_at="",
            updated_at="",
        )
    
    return GeneralSettingsRead(**data)


def update_settings(tenant_id: str, data: GeneralSettingsUpdate) -> GeneralSettingsRead:
    """
    Update general settings for a tenant.
    Creates record if it doesn't exist.
    """
    # Convert Pydantic model to dict, excluding None values for partial updates
    update_dict = data.model_dump(exclude_unset=True)
    
    # Ensure name is set (required field)
    if "name" not in update_dict or not update_dict["name"]:
        existing = get_general_settings(tenant_id)
        if existing and existing.get("name"):
            update_dict["name"] = existing["name"]
        else:
            update_dict["name"] = "Unnamed Organization"
    
    result = upsert_general_settings(tenant_id, update_dict)
    return GeneralSettingsRead(**result)
```

### 5. LLM Inspector Service

**File:** `app/services/llm_inspector_service.py`

```python
from __future__ import annotations
import json
import re
import httpx
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from core.config import settings


async def extract_website_content(url: str, timeout: int = 10) -> str:
    """
    Fetch and extract main text content from a website URL.
    """
    # Validate URL
    parsed = urlparse(url)
    if not parsed.scheme:
        raise ValueError("URL must include scheme (http:// or https://)")
    
    # Fetch HTML
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; Annie-AI/1.0; +https://annie-ai.app)"
        })
        response.raise_for_status()
        html = response.text
    
    # Extract text using BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    
    # Remove script and style elements
    for script in soup(["script", "style", "meta", "link"]):
        script.decompose()
    
    # Get text and clean up whitespace
    text = soup.get_text()
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = " ".join(chunk for chunk in chunks if chunk)
    
    # Limit text length (LLM context limits)
    if len(text) > 10000:
        text = text[:10000] + "..."
    
    return text


async def autofill_from_url(website_url: str) -> dict:
    """
    Extract organization information from a website URL using OpenAI.
    """
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not configured")
    
    # Extract website content
    content = await extract_website_content(website_url)
    
    if not content or len(content.strip()) < 50:
        raise ValueError("Website content too short or empty")
    
    # Prepare prompt for OpenAI
    prompt = f"""Analyze the following website content and extract organization information. 
Return ONLY a valid JSON object with these exact fields (use null for missing information):
{{
  "name": "Organization name",
  "short_description": "Brief description (1-2 sentences)",
  "mission": "Mission statement",
  "vision": "Vision statement", 
  "purpose": "Overall purpose of the organization",
  "customer_problems": "Problems that customers typically face (list or paragraph)"
}}

Website content:
{content[:8000]}

Return only the JSON object, no additional text:"""

    # Call OpenAI API
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that extracts structured information from website content. Always return valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.3,
                "max_tokens": 1000,
            }
        )
        response.raise_for_status()
        result = response.json()
        
        # Extract and clean JSON
        content_text = result["choices"][0]["message"]["content"].strip()
        
        # Remove markdown code blocks if present
        if content_text.startswith("```json"):
            content_text = content_text[7:]
        if content_text.startswith("```"):
            content_text = content_text[3:]
        if content_text.endswith("```"):
            content_text = content_text[:-3]
        content_text = content_text.strip()
        
        # Parse JSON
        try:
            extracted = json.loads(content_text)
        except json.JSONDecodeError:
            # Try to extract JSON from text
            json_match = re.search(r'\{[^{}]*\}', content_text, re.DOTALL)
            if json_match:
                extracted = json.loads(json_match.group())
            else:
                raise ValueError("Failed to parse JSON from LLM response")
        
        # Return extracted fields
        return {
            "name": extracted.get("name"),
            "short_description": extracted.get("short_description"),
            "mission": extracted.get("mission"),
            "vision": extracted.get("vision"),
            "purpose": extracted.get("purpose"),
            "customer_problems": extracted.get("customer_problems"),
        }
```

### 6. FastAPI Routes

**File:** `app/api/v1/settings_general.py`

```python
from __future__ import annotations
from fastapi import APIRouter, Depends
from core.auth import Authed
from core.roles import require_min_role
from core.errors import http_error, ErrorCode
from services.settings_service import get_settings, update_settings
from services.llm_inspector_service import autofill_from_url
from schemas.settings import (
    GeneralSettingsRead,
    GeneralSettingsUpdate,
    AutofillRequest,
    AutofillResponse,
)

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])


@router.get("/general", response_model=GeneralSettingsRead)
def get_general_settings(
    auth: Authed = Depends(require_min_role("observer")),
) -> GeneralSettingsRead:
    """
    Get general settings for the current tenant.
    
    RBAC: require_min_role("observer") - All roles can read
    Returns default values if no settings exist yet (lazy creation).
    """
    return get_settings(auth.tenant_id)


@router.put("/general", response_model=GeneralSettingsRead)
def update_general_settings(
    data: GeneralSettingsUpdate,
    auth: Authed = Depends(require_min_role("admin")),
) -> GeneralSettingsRead:
    """
    Update general settings for the current tenant.
    
    RBAC: require_min_role("admin") - Only admin/owner can write
    Creates record if it doesn't exist (lazy creation).
    """
    return update_settings(auth.tenant_id, data)


@router.post("/general/autofill-from-url", response_model=AutofillResponse)
async def autofill_from_website_url(
    request: AutofillRequest,
    auth: Authed = Depends(require_min_role("admin")),
) -> AutofillResponse:
    """
    Extract organization information from a website URL using LLM.
    
    RBAC: require_min_role("admin") - Only admin/owner can trigger
    Does NOT persist to database; only returns suggestions.
    """
    try:
        extracted = await autofill_from_url(request.website_url)
        return AutofillResponse(**extracted)
    except ValueError as e:
        raise http_error(
            status_code=400,
            code=ErrorCode.BAD_REQUEST,
            message=str(e),
        )
    except RuntimeError as e:
        raise http_error(
            status_code=500,
            code=ErrorCode.INTERNAL_ERROR,
            message=str(e),
        )
    except Exception as e:
        raise http_error(
            status_code=500,
            code=ErrorCode.INTERNAL_ERROR,
            message=f"Unexpected error during autofill: {str(e)}",
        )
```

## 🔒 RBAC Integration

All endpoints use the existing RBAC system:

- **GET /settings/general**: `require_min_role("observer")` 
  - ✅ observer, agent, admin, owner can read
  
- **PUT /settings/general**: `require_min_role("admin")`
  - ✅ admin, owner can write
  
- **POST /settings/general/autofill-from-url**: `require_min_role("admin")`
  - ✅ admin, owner can trigger autofill

## 📁 File Structure

```
app/
├── db/
│   └── general_settings_schema.sql          # SQL migration
├── domain/
│   └── sqlalchemy_models.py                 # SQLAlchemy model (GeneralSettings)
├── schemas/
│   └── settings.py                          # Pydantic schemas
├── repositories/
│   └── general_settings_repo.py             # Database operations
├── services/
│   ├── settings_service.py                 # Business logic
│   └── llm_inspector_service.py             # LLM extraction
└── api/v1/
    └── settings_general.py                   # FastAPI routes
```

## ✅ Complete Implementation

All components are implemented and integrated:
- ✅ SQLAlchemy model
- ✅ Database migration
- ✅ Pydantic schemas
- ✅ Service layer
- ✅ LLM inspector service
- ✅ FastAPI routes with RBAC
- ✅ Router registered in `main.py`
- ✅ Dependencies in `requirements.txt`

