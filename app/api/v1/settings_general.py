"""
Settings → General endpoints.

Follows Layer 2, Layer 3, and Layer 4 rules:
- Settings read → min role observer
- Settings write → min role admin
- All queries MUST be tenant-scoped
- ALWAYS use Pydantic models for request/response
- Never allow cross-tenant access
"""
from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from core.auth import auth_required, Authed
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
    
    Follows Layer 2 rules:
    - Settings read → min role observer
    - Tenant isolation enforced via auth.tenant_id
    
    Returns default values if no settings exist yet (lazy creation).
    
    Args:
        auth: Authenticated user context (min role: observer)
    
    Returns:
        GeneralSettingsRead with current settings or defaults
    """
    return get_settings(auth.tenant_id)


@router.put("/general", response_model=GeneralSettingsRead)
def update_general_settings(
    data: GeneralSettingsUpdate,
    auth: Authed = Depends(require_min_role("admin")),
) -> GeneralSettingsRead:
    """
    Update general settings for the current tenant.
    
    Follows Layer 2 and Layer 3 rules:
    - Settings write → min role admin
    - Tenant isolation enforced via auth.tenant_id
    - Input validation with Pydantic
    
    Creates record if it doesn't exist (lazy creation).
    
    Args:
        data: Settings update data (all fields optional for partial updates)
        auth: Authenticated user context (min role: admin)
    
    Returns:
        Updated GeneralSettingsRead
    """
    return update_settings(auth.tenant_id, data)


@router.post("/general/autofill-from-url", response_model=AutofillResponse)
async def autofill_from_website_url(
    request: AutofillRequest,
    auth: Authed = Depends(require_min_role("admin")),
) -> AutofillResponse:
    """
    Extract organization information from a website URL using LLM.
    
    Follows Layer 2 rules:
    - Only admin/owner can trigger autofill
    - Tenant isolation enforced (implicit via auth)
    
    This endpoint does NOT persist to database; it only returns suggestions.
    The frontend should merge/override current values as needed.
    
    Args:
        request: Autofill request with website_url
        auth: Authenticated user context (min role: admin)
    
    Returns:
        AutofillResponse with extracted information
    
    Raises:
        HTTPException: 400 for invalid URL or extraction failure, 500 for server errors
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

