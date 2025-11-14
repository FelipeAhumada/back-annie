from pydantic import BaseModel

class User(BaseModel):
    id: str
    email: str
    password_hash: str
    is_active: bool

class TenantRole(BaseModel):
    tenant_id: str
    tenant_name: str
    role_name: str
