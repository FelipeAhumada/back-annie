# RBAC Implementation Guide - Annie-AI Backend

## Overview

This document describes the complete RBAC (Role-Based Access Control) implementation for the Annie-AI multi-tenant CRM backend.

## Architecture

### Roles Hierarchy

The system uses 4 roles with the following hierarchy (higher privilege = lower number):

1. **owner** (Level 0) - Full access, can delete organization, manage billing
2. **admin** (Level 1) - Administrative access, can manage members, channels, campaigns
3. **agent** (Level 2) - Can manage leads, respond to conversations, view analytics
4. **observer** (Level 3) - Read-only access, can view but cannot make changes

### Database Schema

#### Tables

1. **users** - System users (can belong to multiple tenants)
2. **tenants** - Organizations/workspaces
3. **roles** - Role definitions (owner, admin, agent, observer)
4. **user_tenants** - Junction table linking users to tenants with roles

#### Key Relationships

- One user can belong to multiple tenants
- Each user-tenant relationship has a specific role
- Roles are tenant-specific (same user can be admin in one tenant, observer in another)

## Implementation Files

### 1. Core RBAC Module (`app/core/roles.py`)

Provides two main dependency functions:

#### `require_min_role(min_role: str)`

Enforces minimum role level using hierarchy:

```python
@router.get("/settings/profile")
def get_settings(auth: Authed = Depends(require_min_role("observer"))):
    # observer, agent, admin, owner can all access
    pass
```

#### `require_roles(*allowed: str)`

Enforces specific role list (no hierarchy):

```python
@router.delete("/settings/organization")
def delete_org(auth: Authed = Depends(require_roles("owner"))):
    # Only owner can access
    pass
```

**Error Response Format:**
```json
{
  "code": "forbidden",
  "message": "You do not have permission for this action",
  "required_roles": ["admin", "owner"],
  "current_role": "agent"
}
```

### 2. Authentication Module (`app/core/auth.py`)

#### `auth_required(req: Request) -> Authed`

FastAPI dependency that:
- Validates JWT token from `Authorization: Bearer <token>` header
- Returns `Authed` object with `user_id`, `tenant_id`, `role`
- Raises structured 401 errors for invalid/missing tokens

#### `sign_jwt(user_id: str, tenant_id: str, role: str) -> str`

Creates JWT token with claims:
- `sub`: user_id
- `tenant_id`: tenant identifier
- `role`: role name (owner, admin, agent, observer)
- `iat`, `exp`: timestamp and expiration

### 3. SQLAlchemy Models (`app/domain/sqlalchemy_models.py`)

ORM models for documentation and future migration:

- `User` - User model
- `Tenant` - Tenant/organization model
- `Role` - Role definitions
- `UserTenant` - Junction table with relationships

### 4. Database Migration (`app/db/annie_rbac_schema.sql`)

Updates roles table to use correct role names:
- owner, admin, agent, observer (replaces old: admin, manager, agent, viewer)

## Usage Examples

### Example 1: Read Settings (Observer+)

```python
from core.roles import require_min_role
from core.auth import auth_required, Authed

@router.get("/settings/profile")
def get_settings(auth: Authed = Depends(require_min_role("observer"))):
    # Any authenticated user with observer role or higher can read
    return {"settings": get_tenant_settings(auth.tenant_id)}
```

### Example 2: Write Settings (Admin+)

```python
@router.put("/settings/profile")
def update_settings(
    data: SettingsUpdate,
    auth: Authed = Depends(require_min_role("admin"))
):
    # Only admin or owner can modify settings
    update_tenant_settings(auth.tenant_id, data)
    return {"ok": True}
```

### Example 3: Destructive Action (Owner Only)

```python
from core.roles import require_roles

@router.delete("/settings/organization")
def delete_organization(auth: Authed = Depends(require_roles("owner"))):
    # Only owner can delete organization
    delete_tenant(auth.tenant_id)
    return {"ok": True}
```

### Example 4: Specific Role List

```python
@router.get("/settings/billing")
def get_billing(auth: Authed = Depends(require_roles("owner", "admin"))):
    # Only owner or admin (not agent or observer)
    return get_billing_info(auth.tenant_id)
```

## Settings Endpoints Rules

Based on Layer 2 rules from `.cursorrules`:

| Operation | Endpoint Pattern | Required Role |
|-----------|-----------------|---------------|
| Read | `GET /settings/*` | `require_min_role("observer")` |
| Write | `PUT/POST /settings/*` | `require_min_role("admin")` |
| Delete Org | `DELETE /settings/organization` | `require_roles("owner")` |
| Billing Critical | `POST /settings/billing/*` | `require_roles("owner", "admin")` |

## Tenant Isolation

**Critical:** All endpoints MUST enforce tenant isolation:

```python
# Always verify tenant_id matches auth.tenant_id
if tenant_id != auth.tenant_id:
    raise http_error(
        status_code=403,
        code=ErrorCode.FORBIDDEN,
        message="Access denied to this tenant",
    )
```

## JWT Token Structure

```json
{
  "sub": "user-uuid",
  "tenant_id": "tenant-id",
  "role": "admin",
  "iat": 1234567890,
  "exp": 1234574490
}
```

## Error Responses

All authorization failures return HTTP 403 with structured JSON:

```json
{
  "code": "forbidden",
  "message": "You do not have permission for this action",
  "required_roles": ["admin", "owner"],
  "current_role": "agent",
  "tenant_id": "tenant-id"
}
```

## Testing RBAC

### Test Cases

1. **Observer can read but not write:**
   ```python
   # Should succeed
   GET /settings/profile (with observer token)
   
   # Should fail with 403
   PUT /settings/profile (with observer token)
   ```

2. **Admin can read and write:**
   ```python
   # Should succeed
   GET /settings/profile (with admin token)
   PUT /settings/profile (with admin token)
   
   # Should fail with 403
   DELETE /settings/organization (with admin token)
   ```

3. **Owner can do everything:**
   ```python
   # All should succeed
   GET /settings/profile (with owner token)
   PUT /settings/profile (with owner token)
   DELETE /settings/organization (with owner token)
   ```

## Migration Steps

1. Run base schema: `app/db/annie_auth_schema.sql`
2. Run RBAC update: `app/db/annie_rbac_schema.sql`
3. Update existing user_tenants to use new role IDs:
   ```sql
   UPDATE user_tenants SET role_id = 1 WHERE role_id = (SELECT id FROM roles WHERE name = 'admin');
   -- etc.
   ```

## Files Reference

- **Core RBAC:** `app/core/roles.py`
- **Authentication:** `app/core/auth.py`
- **Error Handling:** `app/core/errors.py`
- **SQLAlchemy Models:** `app/domain/sqlalchemy_models.py`
- **Migration:** `app/db/annie_rbac_schema.sql`
- **Examples:** `app/api/v1/settings_examples.py`

## Notes

- The current codebase uses `psycopg2` directly, not SQLAlchemy ORM
- SQLAlchemy models are provided for documentation and future migration
- All role checks happen at the FastAPI dependency level
- Tenant isolation is enforced in every endpoint that accesses tenant data
- JWT tokens include role information, but role is verified against database when needed

